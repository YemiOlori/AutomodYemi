"""
moderation_tools.py

RTC: For voice communication
"""

import logging
import threading
import json
from datetime import datetime
from configparser import ConfigParser

import pytz
import boto3

from .clubhouse_api import Clubhouse


def read_config(section):
    """
    A function to read the config file.
    :param filename: The file to be read.
    :return config: List
    """
    config_object = ConfigParser()
    config_object.read("/Users/deon/Documents/GitHub/HQ/config.ini")

    config_object = config_object[section]

    if section == "Account" or section == "S3":
        return dict(config_object)

    content_list = []
    for item in config_object:
        content_list.append(config_object[item])

    return content_list


# Load user config settings from AutoMod/mod_config.py
# Read config.in
class Var:
    active_speaker = False
    waiting_speaker = False
    active_mod = False
    waiting_mod = False

    mod_channel_thread = None
    announce_thread = None
    wait_speaker_thread = None
    listen_ping_thread = None
    music_thread = None
    welcome_thread = None

    already_welcomed_list = []
    counter = 0

    mod_list = read_config("ModList")
    guest_list = read_config("GuestList") + read_config("ASocialRoomGuestList")
    approved_ping_list = read_config("ApprovedPing")

    client_id = read_config("Account")["user_id"]

    s3_bucket = read_config("S3")["bucket"]


def set_interval(interval):
    """
    A function to set the interval decorator.

    :param interval: The time interval in seconds.
    :return decorator:
    """
    def decorator(func):
        def wrap(*args, **kwargs):
            stopped = threading.Event()

            def loop():
                while not stopped.wait(interval):
                    run = func(*args, **kwargs)
                    if not run:
                        logging.info(f"moderation_tools.set_interval Stopped: {func}")
                        break

            thread = threading.Thread(target=loop)
            thread.daemon = True
            thread.start()
            logging.info(f"moderation_tools.set_interval Started: {func}")

            return stopped

        return wrap

    return decorator


@set_interval(30)
def ping_keep_alive_client(client, channel_name):
    """ (str) -> bool

    Continue to ping alive every 30 seconds.
    """
    client.active_ping(channel_name)
    return True


def data_dump(dump, source, channel=""):

    dump_loaded = False
    log = f"moderation_tools.data_dump Dumped {source} {channel}"

    if source == 'feed':
        if dump['items']:
            data = dump
            key = source
            dump_loaded = True
        else:
            log = dump

    elif source == 'channel':
        if dump['success']:
            data = dump
            key = f"channel_{dump['channel']}"
            dump_loaded = True
        else:
            log = dump

    elif source == 'channel_dict':
        if dump['channel_info']['success']:
            data = dump
            key = f"channel_{dump['channel_info']['channel']}"
            dump_loaded = True
        else:
            log = dump

    elif source == 'join':
        if dump['users']:
            data = dump
            key = f"join_{dump['channel']}"
            dump_loaded = True
        else:
            log = dump

    else:
        data = dump
        key = "unrecognized"
        dump_loaded = True
        log = f"moderation_tools.data_dump Dumping from {source} not recognized"

    if dump_loaded:
        s3_client = boto3.client('s3')
        data = json.dumps(data)
        bucket = Var.s3_bucket
        timestamp = datetime.now(pytz.timezone('UTC')).isoformat()
        key = f"{key}_{timestamp}.json"

        s3_client.put_object(
            Body=data,
            Bucket=bucket,
            Key=key,
        )

    logging.info(log)

    return


def data_dump_client(client, dump=None, source=None, channel=""):
    is_private = False
    is_social_mode = False

    if dump:
        if source == "join":
            is_private = dump["is_private"]
            is_social_mode = dump["is_social_mode"]

        elif source == "channel":
            is_private = dump["is_private"]
            is_social_mode = dump["is_social_mode"]

        elif source == "channel_dict":
            is_private = dump["channel_info"]["is_private"]
            is_social_mode = dump["channel_info"]["is_social_mode"]

        if not is_private and not is_social_mode:
            data_dump(dump, source, channel)

    else:
        feed_info = client.get_feed()
        data_dump(feed_info, 'feed')

        channel_info = client.get_channel(channel)
        if not channel_info['is_social_mode'] and not channel_info['is_private']:
            data_dump(channel_info, 'channel', channel)

    return


def send_room_chat(client, channel, message):

    if isinstance(message, str):
        client.send_channel_message(channel, message)
        logging.info(f"moderation_tools.send_room_chat Sent channel message: {message}")

    if isinstance(message, list):
        for m in message:
            client.send_channel_message(channel, m)
            logging.info(f"moderation_tools.send_room_chat channel message: {m}")

    return


# Figure out how to input the announcement interval
def set_announcement(client, channel, message, interval):

    @set_interval(interval)
    def announcement(client=client, channel=channel, message=message):

        channel_info = client.get_channel(channel)

        if channel_info['success']:
            send_room_chat(client, channel, message)
        else:
            return False

        return True

    return announcement()


def get_channel_status(client, channel):

    response_dict = {
        'client_info': None,
        'channel_info': None,
        'user_info': None,
    }

    try:
        channel_info = client.get_channel(channel)

    except TimeoutError:
        logging.info("moderation_tools.get_channel_status No channel info retrieved")

    else:
        if not channel_info['success']:

            Var.active_mod = False
            logging.info("moderation_tools.get_channel_status Changed active_mod to False")

            Var.listen_ping_thread = listen_channel_ping(client)
            logging.info("moderation_tools.get_channel_status Enabled listen_channel_ping")

        else:
            i = 0
            user_info = channel_info.pop('users')
            for user in user_info:
                user_id = user['user_id']

                if str(user_id) == Var.client_id:

                    client = user_info.pop(i)

                    response_dict['client_info'] = client
                    response_dict['channel_info'] = channel_info
                    response_dict['user_info'] = user_info

                    break

                i += 1

    return response_dict


@set_interval(10)
def wait_speaker_permission(client, channel, user_id):
    """ (str) -> bool

    Function that runs when you've requested for a voice permission.
    """

    # Check if the moderator allowed your request.
    res_inv = client.accept_speaker_invite(channel, user_id)
    if res_inv['success']:
        Var.active_speaker = True
        return False

    return True


def request_speaker_permission(client, channel, channel_dict, join_dict, mod=False, music=False):

    creator_id = join_dict['creator_user_profile_id']
    creator_name = ""
    for user in join_dict['users']:
        if creator_id == user['user_id']:
            creator_name = user['first_name']
            break

    message = "🤖 Hello " + creator_name + "! I'm AutoMod! 🎉"
    send_room_chat(client, channel, message)
    message = False

    client_info = channel_dict['client_info']
    logging.info(f"moderation_tools.request_speaker_permission {client_info}")

    if not client_info['is_speaker']:

        client.audience_reply(channel)
        logging.info("moderation_tools.request_speaker_permission Triggered clubhouse_api.Clubhouse.audience_reply")

        if mod:
            message = "If you'd like to use my features, please invite me to speak and make me a Moderator."

        elif music:
            message = "If you'd like to hear music, please invite me to speak."

        Var.wait_speaker_thread = wait_speaker_permission(client, channel, Var.client_id)

    elif not client_info['is_moderator']:
        if mod:
            message = "If you'd like to use my features, please make me a Moderator."

    if message:
        send_room_chat(client, channel, message)
        logging.info(f"moderation_tools.request_speaker_permission Triggered message {message}")

    return


def welcome_guests(client, channel, user):

    name = user['first_name']
    message = f"Welcome {name}! 🎉"

    if user['user_id'] == 1414736198:
        message = 'Tabi! Hello my love! 😍'

    if user['user_id'] == 2247221:
        message_2 = 'First'
        message_3 = 'And furthermore, infinitesimal'
        message = [message, message_2, message_3]

    send_room_chat(client, channel, message)

    Var.already_welcomed_list.append(user['user_id'])

    return


def invite_guests(client, channel, user):
    if not user['is_speaker'] and not user['is_invited_as_speaker']:
        client.invite_speaker(channel, user['user_id'])
        logging.info(f"moderation_tools.invite_guests Invited {user['name']} to speak")

        welcome_guests(client, channel, user)

    return


def mod_guests(client, channel, user):
    if user['is_speaker'] and not user['is_moderator']:
        client.make_moderator(channel, user['user_id'])
        logging.info(f"moderation_tools.mod_guest Made {user['name']} a moderator")

        if user not in Var.already_welcomed_list:
            welcome_guests(client, channel, user)

    return


def termination(client, channel):
    client.leave_channel(channel)

    Var.active_speaker = False
    Var.waiting_speaker = False
    Var.active_mod = False
    Var.waiting_mod = False

    if Var.mod_channel_thread:
        Var.mod_channel_thread.set()

    if Var.announce_thread:
        Var.announce_thread.set()

    if Var.music_thread:
        Var.music_thread.set()

    if Var.welcome_thread:
        Var.welcome_thread.set()

    if Var.ping_keep_alive_thread:
        Var.ping_keep_alive_thread.set()

    Var.listen_ping_thread = listen_channel_ping(client)

    logging.info("moderation_tools.terminate_mod Automation terminated")

    return


@set_interval(15)
def mod_client(client, channel):
    channel_dict = get_channel_status(client, channel)
    channel_info = channel_dict['channel_info']
    user_info = channel_dict['user_info']

    if Var.counter == 5:
        Var.counter = 0

    # Need exception handling
    if not channel_info or not channel_info['success']:
        termination(client, channel)
        return False

    else:
        client_speaker_status = channel_dict['client_info']['is_speaker']
        client_mod_status = channel_dict['client_info']['is_moderator']
        social_mode = channel_info['is_social_mode']
        private = channel_info['is_private']

        if Var.active_mod and not client_speaker_status:
            client.accept_speaker_invite(channel, Var.client_id)
            logging.info("moderation_tools.mod_channel Client is no longer a speaker")
            logging.info("moderation_tools.mod_channel Client attempted to accept new speaker invitation")

            if client_speaker_status:
                logging.info("moderation_tools.mod_channel Client accepted new speaker invitation")

        elif Var.active_mod and not client_mod_status and not social_mode and Var.counter == 4:
            logging.info(f"moderation_tools.mod_channel Client is not a moderator")
            Var.waiting_mod = True

        if Var.waiting_mod and not client_mod_status and not social_mode and Var.counter == 3:
            termination(client, channel)
            logging.info("moderation_tools.mod_channel Triggered terminate_mod")
            return False

        Var.active_mod = True

        for _user in user_info:
            user_id = _user['user_id']

            if social_mode:
                if user_id not in Var.alreay_welcomed_list:
                    welcome_guests(client, channel, _user)

            elif private:
                if client_mod_status:
                    invite_guests(client, channel, _user)
                    mod_guests(client, channel, _user)

            elif channel_info['club'] and channel_info['club']['club_id'] == 863466177:
                invite_guests(client, channel, _user)

            else:
                if client_mod_status and Var.guest_list:
                    if str(user_id) in Var.guest_list:
                        invite_guests(client, channel, _user)

                if client_mod_status and Var.mod_list:
                    if str(user_id) in Var.mod_list:
                        mod_guests(client, channel, _user)

        if not channel_info['is_social_mode'] and not channel_info['is_private'] and Var.counter == 4:
            feed_info = client.get_feed()
            data_dump(feed_info, 'feed')
            data_dump(channel_dict, 'channel_dict', channel)

        Var.counter += 1

    return True


@set_interval(30)
def music_client(client, channel):
    channel_dict = get_channel_status(client, channel)
    client_info = channel_dict["client_info"]
    client_speaker_status = client_info["is_speaker"]

    if Var.counter == 7:
        Var.counter = 0

    if Var.active_speaker and not client_speaker_status:
        client.accept_speaker_invite(channel, Var.client_id)
        logging.info("moderation_tools.mod_channel Client is no longer a speaker")
        logging.info("moderation_tools.mod_channel Client attempted to accept new speaker invitation")

        if client_speaker_status:
            logging.info("moderation_tools.mod_channel Client accepted new speaker invitation")

    if Var.active_speaker and not client_speaker_status and Var.counter == 4:
        Var.waiting_speaker = True

    if Var.waiting_speaker and not client_speaker_status and Var.counter == 7:
        termination(client, channel)
        logging.info("moderation_tools.mod_channel Triggered terminate_mod")
        return False

    if Var.counter == 6:
        feed_info = client.get_feed()
        data_dump_client(client, feed_info, 'feed')
        data_dump_client(client, channel_dict, "channel_dict", channel)

    Var.counter += 1

    return


@set_interval(180)
def track_room_client(client, channel):
    join_dict = client.join_channel(channel)
    data_dump(join_dict, 'join', channel)

    return True


@set_interval(30)
def welcome_all_client(client, channel):
    channel_dict = get_channel_status(client, channel)
    channel_info = channel_dict["channel_info"]
    user_info = channel_dict["user_info"]

    if Var.counter == 7:
        Var.counter = 0

    for _user in user_info:
        user_id = _user["user_id"]
        if user_id not in Var.alreay_welcomed_list:
            welcome_guests(client, channel, _user)

    if not channel_info or not channel_info["success"]:
        termination(client, channel)
        return False

    if Var.counter == 6:
        feed_info = client.get_feed()
        data_dump_client(client, feed_info, 'feed')
        data_dump_client(client, channel_dict, "channel_dict", channel)

    Var.counter += 1

    return


def automation(client, channel, task=None, announcement=None, interval=3600):
    join_dict = client.join_channel(channel)
    data_dump(join_dict, 'join', channel)
    client.active_ping(channel)
    Var.counter = 0

    channel_dict = get_channel_status(client, channel)
    data_dump(channel_dict, 'channel_dict', channel)

    if task == "mod":
        channel_dict = get_channel_status(client, channel)
        request_speaker_permission(client, channel, channel_dict, join_dict, mod=True)
        Var.mod_channel_thread = mod_client(client, channel)
        Var.ping_keep_alive_thread = ping_keep_alive_client(client, channel)

    elif task == "music":
        request_speaker_permission(client, channel, channel_dict, join_dict, music=True)
        Var.music_thread = music_client(client, channel)
        Var.ping_keep_alive_thread = ping_keep_alive_client(client, channel)

    elif task == "track":
        Var.track_thread = track_room_client(client, channel)

    elif task == "welcome":
        Var.welcome_thread = welcome_all_client(client, channel)
        Var.ping_keep_alive_thread = ping_keep_alive_client(client, channel)

    if announcement:
        # send_room_chat(client, channel, announcement)
        Var.announce_thread = set_announcement(client, channel, announcement, interval)

    elif channel_dict["channel_info"]["is_private"]:
        message_1 = "The share url for this room is"
        message_2 = f"https://www.clubhouse.com/room/{channel}"
        announcement = [message_1, message_2]

        send_room_chat(client, channel, announcement)
        Var.announce_thread = set_announcement(client, channel, announcement, interval)

    if Var.listen_ping_thread:
        Var.listen_ping_thread.set()

    return join_dict


@set_interval(30)
def listen_channel_ping(client):
    """
    A function listen for active ping from user on approved ping list.

    :param client: A Clubhouse object.
    :param active_mod:
    :param ping_list:
    :return decorator:
    :rtype: Dictionary
    """
    # If not active mod
    # Is this redundant with active mod?
    # Check for ping.

    if Var.active_mod:
        logging.info("moderation_tools.listen_channel_ping Response: active_mod is True")
        return False

    else:
        respond = False
        notifications = client.get_notifications()
        for notification in notifications['notifications'][:5]:
            if notification['type'] == 9:
                _user_id = str(notification['user_profile']['user_id'])
                _user_name = notification['user_profile']['name']
                _channel = notification['channel']
                _message = notification['message']

                time_created = notification['time_created']
                time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
                time_now = datetime.now(pytz.timezone('UTC'))
                time_diff = time_now - time_created
                time_diff = time_diff.total_seconds()

                if time_diff < 30 and _user_id in Var.approved_ping_list:
                    respond = True
                    logging.info(f"moderation_tools.listen_channel_ping {_channel} {_user_name} {_message}")

                if respond:
                    automation(client, _channel, "mod",)
                    logging.info("moderation_tools.listen_channel_ping Triggered active_mod_channel")
                    return False

    return True








