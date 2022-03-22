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

active_mod = False
waiting_mod = False
active_mod_thread = None
announce_thread = None
wait_speaker_thread = None
listen_ping_thread = None
welcomed_list_old = []
_counter = 0

tracking_client = boto3.client('s3')


# Load user config settings from AutoMod/mod_config.py
# Read config.ini
def read_config(section):
    """
    A function to read the config file.
    :param filename: The file to be read.
    :return config: List
    """
    config_object = ConfigParser()
    config_object.read("/Users/deon/Documents/GitHub/HQ/config.ini")

    config_object = config_object[section]

    if section == "Account":
        return dict(config_object)

    content_list = []
    for item in config_object:
        content_list.append(config_object[item])

    return content_list


mod_list = read_config("ModList")
guest_list = read_config("GuestList")
approved_ping_list = read_config("ApprovedPing")
client_id = read_config("Account")
client_id = client_id['user_id']


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
        bucket = 'iconicbucketch'
        timestamp = datetime.now(pytz.timezone('UTC')).isoformat()
        key = f"{key}_{timestamp}.json"

        s3_client.put_object(
            Body=data,
            Bucket=bucket,
            Key=key,
        )

    logging.info(log)

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

            global active_mod
            active_mod = False
            logging.info("moderation_tools.get_channel_status Changed active_mod to False")

            global listen_ping_thread
            listen_ping_thread = listen_channel_ping(client)
            logging.info("moderation_tools.get_channel_status Enabled listen_channel_ping")

        else:
            i = 0
            user_info = channel_info.pop('users')
            for _user in user_info:
                _user_id = _user['user_id']

                if str(_user_id) ==  client_id:

                    _client = user_info.pop(i)

                    response_dict['client_info'] = _client
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
        return False

    return True


def request_speaker_permission(client, channel, channel_dict, join_dict, mod=True, music=False):

    creator_id = join_dict['creator_user_profile_id']
    creator_name = ""
    for _user in join_dict['users']:
        if creator_id == _user['user_id']:
            creator_name = _user['first_name']
            break

    message = "🤖 Hello " + creator_name + "! I'm AutoMod! 🎉"
    send_room_chat(client, channel, message)

    channel_info = channel_dict['channel_info']

    client_info = channel_dict['client_info']
    logging.info(f"moderation_tools.request_speaker_permission {client_info}")

    if not client_info['is_speaker']:

        client.audience_reply(channel)
        logging.info("moderation_tools.request_speaker_permission Triggered clubhouse_api.Clubhouse.audience_reply")

        if mod:
            message = "If you'd like to use my features, please invite me to speak and make me a Moderator."

        elif not mod and music:
            message = "If you'd like to hear music, please invite me to speak."

        send_room_chat(client, channel, message)
        global wait_speaker_thread
        wait_speaker_thread = wait_speaker_permission(client, channel, client_id)
        logging.info(f"moderation_tools.request_speaker_permission Triggered message {message}")

    if client_info['is_speaker'] and not client_info['is_moderator']:
        if mod:
            message = 'Please make me a Moderator.'
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

    global welcomed_list_old
    welcomed_list_old.append(user['user_id'])

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

        if user not in welcomed_list_old:
            welcome_guests(client, channel, user)

    return


def terminate_mod(client, channel):

    global active_mod
    active_mod = False

    global waiting_mod
    waiting_mod = False

    if announce_thread:
        announce_thread.set()

    if active_mod_thread:
        active_mod_thread.set()

    client.leave_channel(channel)

    logging.info("moderation_tools.terminate_mod Active mod terminated")

    global listen_ping_thread
    listen_ping_thread = listen_channel_ping(client)

    return


@set_interval(15)
def mod_channel(client, channel):

    channel_dict = get_channel_status(client, channel)
    channel_info = channel_dict['channel_info']

    user_info = channel_dict['user_info']
    global waiting_mod
    global active_mod
    global _counter

    if _counter == 5:
        _counter = 0

    if not channel_info or not channel_info['success']:
        terminate_mod(client, channel)
        return False

    else:
        logging.info(f"moderation_tools.mod_channel Counter: {_counter}")
        client_speaker_status = channel_dict['client_info']['is_speaker']
        client_mod_status = channel_dict['client_info']['is_moderator']
        social_mode = channel_info['is_social_mode']

        if active_mod and not client_speaker_status:
            client.accept_speaker_invite(channel, client_id)
            logging.info("moderation_tools.mod_channel Client is no longer a speaker")
            logging.info("moderation_tools.mod_channel Client attempted to accept new speaker invitation")

            if client_speaker_status:
                logging.info("moderation_tools.mod_channel Client accepted new speaker invitation")

        elif active_mod and not client_mod_status and not social_mode and _counter == 4:
            logging.info(f"moderation_tools.mod_channel Client is not a moderator")
            waiting_mod = True

        if waiting_mod and not client_mod_status and not social_mode and _counter == 3:
            terminate_mod(client, channel)
            logging.info("moderation_tools.mod_channel Triggered terminate_mod")
            return False

        active_mod = True

        for _user in user_info:
            _user_id = _user['user_id']

            if social_mode:
                if _user_id not in welcomed_list_old:
                    welcome_guests(client, channel, _user)

            elif channel_info['is_private']:
                if client_mod_status:
                    invite_guests(client, channel, _user)
                    mod_guests(client, channel, _user)

            else:
                if client_mod_status and guest_list:
                    if str(_user_id) in guest_list:
                        invite_guests(client, channel, _user)

                if client_mod_status and mod_list:
                    if str(_user_id) in mod_list:
                        mod_guests(client, channel, _user)

        if _counter == 1 or _counter == 3:
            client.active_ping(channel)
            logging.info("moderation_tools_v2.mod_channel Triggered clubhouse_api.Clubhouse.active_ping")

        if not channel_info['is_social_mode'] and not channel_info['is_private'] and _counter == 4:
            feed_info = client.get_feed()
            data_dump(feed_info, 'feed')
            data_dump(channel_info, 'channel', channel)

        _counter += 1

    return True


def active_mod_channel(client, channel, announcement=None, interval=3600):

    join_dict = client.join_channel(channel)
    client.active_ping(channel)

    data_dump(join_dict, 'join', channel)

    channel_dict = get_channel_status(client, channel)
    request_speaker_permission(client, channel, channel_dict, join_dict)

    global active_mod_thread
    active_mod_thread = mod_channel(client, channel)
    # global ping_keep_alive_thread
    # ping_keep_alive_thread = ping_keep_alive(client, channel)

    global announce_thread
    if announcement:
        send_room_chat(client, channel, announcement)
        announce_thread = set_announcement(client, channel, announcement, interval)

    elif channel_dict['channel_info']['is_private']:
        message_1 = 'The share url for this room is'
        message_2 = 'https://www.clubhouse.com/room/' + channel
        announcement = [message_1, message_2]

        send_room_chat(client, channel, announcement)
        announce_thread = set_announcement(client, channel, announcement, interval)

    else:
        if announce_thread:
            announce_thread.set()

    global listen_ping_thread
    if listen_ping_thread:
        listen_ping_thread.set()

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

    if active_mod:
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

                if time_diff < 30 and _user_id in approved_ping_list:
                    respond = True
                    logging.info(f"moderation_tools.listen_channel_ping {_channel} {_user_name} {_message}")

                if respond:
                    active_mod_channel(client, _channel)
                    logging.info("moderation_tools.listen_channel_ping Triggered active_mod_channel")
                    return False

    return True








