"""
moderation.py

RTC: For voice communication
"""

import logging
import threading
import json
import time
from datetime import datetime
from configparser import ConfigParser


import pytz
import boto3

from .clubhouse import Clubhouse


def load_config(config_file=""):
    """A function to read the config file."""
    config_object = ConfigParser()
    config_object.read(config_file)
    return config_object


def section_key_exception(config_object, section):
    if section not in config_object.sections():
        raise Exception(f"Error in fetching config in read_config method. {section} not found in config file.")


def config_to_dict(config_object, section, item=None):
    section_key_exception(config_object, section)
    config_section = dict(config_object[section])
    if not item:
        return config_section
    config_item = config_section[item]
    # Return None if section does not exist
    return config_item


def config_to_list(config_object, section):
    section_key_exception(config_object, section)
    config_section = config_object[section]
    item_list = []
    for item in config_section:
        item_list.append(item)
    config_section = item_list
    # Return None if section does not exist
    return config_section


def set_interval(interval):
    """
    A function to set the interval decorator.

    :param interval: The interval duration
    :type interval: int
    :return: decorator
    :rtype: function
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
                return stopped
            return wrap
        return decorator


class ModClient(Clubhouse):
    """

    """

    def __init__(self):
        """

        """
        super().__init__()
        self.client_id = self.HEADERS.get('CH-UserID')

        config_file = "/Users/deon/Documents/GitHub/HQ/config.ini"
        config_object = load_config(config_file)
        self.s3_bucket = config_to_dict(config_object, "S3", "bucket")
        self.respond_ping_list = config_to_list(config_object, "RespondPing")
        self.mod_list = config_to_list(config_object, "ModList")
        self.guest_list = (config_to_list(config_object, "GuestList")
                           + config_to_list(config_object, "ASocialRoomGuestList"))

        self.active_speaker = False
        self.active_mod = False
        self.waiting_speaker = False
        self.waiting_mod = False

        self.waiting_ping_thread = None
        self.waiting_speaker_thread = None
        self.channel_mod_thread = None
        self.announcement_thread = None
        self.music_thread = None
        self.welcome_thread = None
        self.keep_alive_thread = None

        self.already_welcomed_list = []
        self.already_in_room_list = []

        self.waiting_speaker_counter = 0
        self.counter = 0

    def __repr__(self):
        pass

    def __str__(self):
        return f"Config: [Clubhouse User ID: {self.client_id}, [Amazon S3 Bucket:" \
               f"{self.s3_bucket}]"

    def s3_client_dump(self, dump, key):
        """
        A function to set the interval decorator.

        :param dump: The server data to be dumped
        :type dump: any
        :param key: A label for the dump file
        :type key: str
        :return: Server response
        :rtype: bool
        """
        if isinstance(dump, dict):
            dump = json.dumps(dump)
        s3_client = boto3.client("s3")
        bucket = self.s3_bucket
        timestamp = datetime.now(pytz.timezone('UTC')).isoformat()
        key = f"{key}_{timestamp}.json"
        run = s3_client.put_object(
            Body=dump,
            Bucket=bucket,
            Key=key,
        )
        response = run.get("success")
        return response

    @set_interval(30)
    def keep_alive_ping(self, channel):
        """
        Continues to active ping service every 30 seconds.

        :param client: client
        :type client: Clubhouse
        :param channel: The channel id for the active channel
        :type channel: str

        :return: Server response
        :rtype: bool
        """
        run = self.active_ping(channel)
        response = run.get("success")
        return response

    def send_room_chat(self, channel, message=str or list):
        """
        Sends a message to the room chat for the active channel

        :param client: client
        :type client: Clubhouse
        :param channel: The channel id for the active channel
        :type channel: str
        :param message: The message or list of messages to send
        :type message: str|list

        :return: Server response
        :rtype: bool
        """
        response = False
        if isinstance(message, str):
            message = [message]
        for item in message:
            run = self.send_channel_message(channel, item)
            response = run.get("success")
            time.sleep(5)
        return response

    def set_announcement(self, channel, message, interval):
        """
        Sends an announcement to the room chat for the active channel each interval

        :param client: client
        :type client: Clubhouse
        :param channel: The channel id for the active channel
        :type channel: str
        :param message: The message or list of messages to send
        :type message: str|list
        :param interval: The interval between announcements in seconds
        :type interval: int

        :return: Server response
        :rtype: bool
        """
        @set_interval(interval)
        def announcement():
            response = self.send_room_chat(channel, message)
            return response
        return announcement()

    def get_join_status(self, channel):

        def room_type(join_info):
            _room_type = "public"
            if join_info.get("is_private"):
                _room_type = "private"
            elif join_info.get("is_social_mode"):
                _room_type = "social"
            return _room_type

        def channel_creator(join_info):
            """


            :rtype
            """
            name = ""
            for user in join_info.get("users"):
                if join_info.get("creator_user_profile_id") == user.get("user_id"):
                    name = user.get("first_name")
                    break
            return name

        join_dict = self.join_channel(channel)
        room_type = room_type(join_dict)
        creator = channel_creator(join_dict)
        response_dict = {
            "type": room_type,
            "creator": creator,
            "join_dict": join_dict,
        }
        return response_dict

    def get_channel_status(self, channel):
        """
        Retrieves information about the active channel

        :param client: client
        :type client: Clubhouse
        :param channel: The channel id for the active channel
        :type channel: str

        :return: Dict with information about the active channel
        :rtype: dict
        """
        def speaker_status(client_dict):
            is_speaker = client_dict.get("is_speaker")
            return is_speaker

        def mod_status(client_dict):
            is_moderator = client_dict.get("is_moderator")
            return is_moderator

        channel_info = self.get_channel(channel)
        user_info = channel_info.pop("users")
        response_dict = {"channel_info": channel_info, "user_info": user_info}

        i = 0
        for user in user_info:
            if str(user.get("user_id")) == self.client_id:
                client_info = user_info.pop(i)
                speaker_status = speaker_status(client_info)
                mod_status = mod_status(client_info)
                response_dict["client_info"] = client_info
                response_dict["client_speaker_status"] = speaker_status
                response_dict["client_mod_status"] = mod_status
                break
            i += 1

        return response_dict

    @set_interval(10)
    def wait_speaker_permission(self, channel):
        """ (str) -> bool

        Function that runs when you've requested for a voice permission.
        """

        # Check if the moderator invited the client to speak.
        accept = self.accept_speaker_invite(channel, self.client_id)
        if accept.get("success"):
            return False
        return True






def run_client_scratch():
    channel = None

    def terminate_client(client, channel):
        client.leave_channel(channel)

        ModClient.active_speaker = False
        ModClient.waiting_speaker = False
        ModClient.active_mod = False
        ModClient.waiting_mod = False

        if ModClient.channel_mod_thread:
            ModClient.channel_mod_thread.set()

        if ModClient.announcement_thread:
            ModClient.announcement_thread.set()

        if ModClient.music_thread:
            ModClient.music_thread.set()

        if ModClient.welcome_thread:
            ModClient.welcome_thread.set()

        if ModClient.keep_alive_thread:
            ModClient.keep_alive_thread.set()

        ModClient.listen_ping_thread = listen_channel_ping(client)

        logging.info("moderation_tools.terminate_mod Automation terminated")

        return

    def set_hello_message(join_dict, channel_dict, mod_channel=False, music=False):
        """Defines which message to send to the room chat upon joining."""











        # client_info = channel_dict.get("client_info")
        creator_name = get_channel_creator(join_dict)
        speaker_status = client_speaker_status(channel_dict)
        mod_status = client_mod_status(channel_dict)

        def request_speak_and_mod():
            message = "If you'd like to use my features, please invite me to speak and make me a Moderator. ✳️"
            return message

        def request_mod():
            message = "If you'd like to use my features, please make me a Moderator. ✳️"
            return message

        def request_speak():
            message = "If you'd like to hear music, please invite me to speak. 🎶"
            return message

        def map_task():
            message = None
            if not speaker_status:
                if mod_channel:
                    message = request_speak_and_mod()
                elif music:
                    message = request_speak()
            elif not mod_status and mod_channel:
                message = request_mod()
            return message

        def set_message():
            message_1 = f"🤖 Hello {creator_name}! I'm AutoMod! 🎉"
            message_2 = map_task()
            message = [message_1, message_2] if message_2 else message_1
            return message

        hello_message = set_message()

        return hello_message


    def welcome_guests(client, channel, user_info):
        name = user_info.get("first_name")
        message = f"Welcome {name}! 🎉"

        if user_info.get("user_id") == 2350087:
            message = f"Welcome Disco Doggie! 🎉"

        elif user_info.get("user_id") == 1414736198:
            message = "Tabi! Hello my love! 😍"

        elif user_info.get("user_id") == 47107:
            message_2 = "Ryan, please don't choose violence today!"
            message = [message, message_2]

        elif user_info.get("user_id") == 2247221:
            message_2 = "First"
            message_3 = "And furthermore, infinitesimal"
            message = [message, message_2, message_3]

        response = send_room_chat(client, channel, message)

        return response


    def invite_guests(client, channel, user_info):
        if not user_info.get("is_speaker") and not user_info.get("is_invited_as_speaker"):
            client.invite_speaker(channel, user_info.get("user_id"))
            welcome_guests(client, channel, user_info)


    def mod_guests(client, channel, user_info):
        if user_info.get("is_speaker") and not user_info.get("is_moderator"):
            client.make_moderator(channel, user_info.get("user_id"))







    join_status = ModClient.get_join_status(channel)
    room_creator = join_status.get("channel_creator")
    client_speaker_status = ModClient.get_channel_status("")
    client_mod_status = ModClient.get_channel_status()













def scratch():

    # Figure out how to avoid this function
    def classify_data_dump(dump, source, channel=""):

        log = f"Dumped {source} {channel}"

        if source == 'feed':
            if dump.get('items'):
                data = dump
                key = source
            else:
                log = dump

        elif source == 'channel':
            if dump.get('success'):
                data = dump
                key = f"channel_{dump['channel']}"
            else:
                log = dump

        elif source == 'channel_dict':
            if dump.get('channel_info'):
                data = dump
                key = f"channel_{dump['channel_info']['channel']}"
            else:
                log = dump

        elif source == 'join':
            if dump.get('users'):
                data = dump
                key = f"join_{dump['channel']}"
            else:
                log = dump

        else:
            data = dump
            key = "unrecognized"
            log = f"Unrecognized dumping source {source}"

        response = {
            "data": data,
            "key": key,
        }

        logging.info(log)

        return response

    # Simplify this also
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
















    @set_interval(30)
    def music_client(client, channel):
        channel_dict = get_channel_status(client, channel)
        client_info = channel_dict["client_info"]
        client_speaker_status = client_info["is_speaker"]

        if Var.counter == 7:
            Var.counter = 0

        if Var.active_speaker and not client_speaker_status:
            client.accept_speaker_invite(channel, Var.client_id)
            logging.info("moderation_tools.mod_channel ModClient is no longer a speaker")
            logging.info("moderation_tools.mod_channel ModClient attempted to accept new speaker invitation")

            if client_speaker_status:
                logging.info("moderation_tools.mod_channel ModClient accepted new speaker invitation")

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
            if user_id not in Var.already_welcomed_list:
                welcome_guests(client, channel, _user)

        if not channel_info or not channel_info["success"]:
            termination(client, channel)
            return False

        if Var.counter == 6:
            feed_info = client.get_feed()
            data_dump_client(client, feed_info, 'feed')
            data_dump_client(client, channel_dict, "channel_dict", channel)

        Var.counter += 1

        return True

    @set_interval(10)
    def urban_dict_client(client, channel):
        games.urban_dict(client, channel)

        return True


    def automation(client, channel, task=None, announcement=None, interval=3600):
        join_dict = client.join_channel(channel)
        data_dump(join_dict, 'join', channel)
        client.active_ping(channel)
        Var.counter = 0

        for _user in join_dict['users']:
            Var.already_in_room_list.append(_user['user_id'])

        logging.info(f"moderation_tools.automation {len(Var.already_in_room_list)} users already in channel")

        channel_dict = get_channel_status(client, channel)
        data_dump(channel_dict, 'channel_dict', channel)

        Var.urban_dict_thread = urban_dict_client(client, channel)

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










