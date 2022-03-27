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
from functools import wraps


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


def reload_user():
    """
    A function to reload Clubhouse client from previous session.

    :param client: A Clubhouse object
    :return client: A Clubhouse object updated with configuration information
    """
    config_file = "/Users/deon/Documents/GitHub/HQ/setting.ini"
    config_object = load_config(config_file)

    user_config = config_to_dict(config_object, "Account")

    user_id = user_config.get("user_id")
    user_token = user_config.get("user_token")
    user_device = user_config.get("user_device")
    refresh_token = user_config.get("refresh_token")
    access_token = user_config.get("access_token")

    # Check if user is authenticated
    client = ModClient()
    # if user_id and user_token and user_device:
    #     client = ModClient(
    #         user_id=user_id,
    #         user_token=user_token,
    #         user_device=user_device,
    #     )
    #     logging.info("Reload client successful")
    # else:
    #     logging.info("Reload client not successful")

    return client


def set_interval(interval):
    """
    A function to set the interval decorator.


    :param interval: The interval duration
    :param timeout:
    :type interval: int
    :return: decorator
    :rtype: function
    """
    def decorator(func):
        # @wraps(func)  # Is this in the right place?
        def wrap(*args, **kwargs):
            is_stopped = threading.Event()

            def loop():
                while not is_stopped.wait(interval):
                    run = func(*args, **kwargs)
                    if not run:
                        logging.info(f"Stopped: {func}")
                        break
            thread = threading.Thread(target=loop)
            thread.daemon = True
            thread.start()
            logging.info(f"Started: {func}")
            return is_stopped
        return wrap
    return decorator


class ModClient(Clubhouse):
    """

    """

    # CONFIG_FILE = "/Users/deon/Documents/GitHub/HQ/config.ini"
    # config_object = load_config(CONFIG_FILE)
    #
    # CLIENT_ID = config_to_dict(config_object, "Account", "user_id")
    # PHONE_NUMBER = config_to_dict(config_object, "Account", "phone_number")
    # S3_BUCKET = config_to_dict(config_object, "S3", "bucket")
    #
    # AUTO_MOD_CLUBS = config_to_list(config_object, "AutoModClubs")
    # SOCIAL_CLUBS = config_to_list(config_object, "SocialClubs")
    # RESPOND_PING_LIST = config_to_list(config_object, "RespondPing")
    # MOD_LIST = config_to_list(config_object, "ModList")
    # GUEST_LIST = (config_to_list(config_object, "GuestList")
    #               + config_to_list(config_object, "ASocialRoomGuestList"))

    config_file = "/Users/deon/Documents/GitHub/HQ/config.ini"
    config_object = load_config(config_file)

    client_id = config_to_dict(config_object, "Account", "user_id")
    phone_number = config_to_dict(config_object, "Account", "phone_number")
    user_device = config_to_dict(config_object, "Account", "user_device")
    user_token = config_to_dict(config_object, "Account", "user_token")

    s3_bucket = config_to_dict(config_object, "S3", "bucket")

    auto_mod_clubs = config_to_list(config_object, "AutoModClubs")
    social_clubs = config_to_list(config_object, "SocialClubs")
    respond_ping_list = config_to_list(config_object, "RespondPing")
    mod_list = config_to_list(config_object, "ModList")
    guest_list = (config_to_list(config_object, "GuestList")
                  + config_to_list(config_object, "ASocialRoomGuestList"))

    waiting_speaker = False
    granted_speaker = False
    active_speaker = False
    waiting_mod = False
    granted_mod = False
    active_mod = False

    waiting_ping_thread = None
    waiting_speaker_thread = None
    waiting_mod_thread = None
    active_mod_thread = None
    announcement_thread = None
    music_thread = None
    welcome_thread = None
    keep_alive_thread = None
    chat_client_thread = None

    already_welcomed_list = []
    already_in_room_list = []

    dump_interval = 0
    dump_counter = 0

    def __init__(self):
        """

        """
        super().__init__(self.client_id, self.user_token, self.user_device)

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
        logging.info(run)
        return response

    def data_dump(self, dump, source, channel=""):
        log = f"Dumped {source} {channel}"
        key = ""

        if source == "feed":
            key = source

        elif source == "channel":
            key = f"channel_{dump.get('channel')}"

        elif source == "channel_dict":
            key = f"channel_{dump.get('channel_info').get('channel')}"

        elif source == 'join':
            key = f"join_{dump.get('channel')}"

        else:
            key = "unrecognized"
            log = f"Unrecognized dumping source {source}"

        logging.info(log)
        response = self.s3_client_dump(dump, key)

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
        self.active_ping(channel)
        return True

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
            time.sleep(3)
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

    def get_join_dict(self, channel):

        def channel_type():
            _channel_type = "public"
            if join_dict.get("is_private"):
                _channel_type = "private"
            elif join_dict.get("is_social_mode"):
                _channel_type = "social"
            return _channel_type

        def channel_creator():
            """


            :rtype
            """
            name = ""
            for user in join_dict.get("users"):
                if join_dict.get("creator_user_profile_id") == user.get("user_id"):
                    name = user.get("first_name")
                    break
            return name

        def club():
            _club = join_dict.get("club").get("club_id")

        join_dict = self.join_channel(channel)
        response_dict = {
            "join_dict": join_dict,
            "type": channel_type(),
            "creator": channel_creator(),
            "club": club(),
        }
        return response_dict

    def get_channel_dict(self, channel):
        """
        Retrieves information about the active channel

        :param client: client
        :type client: Clubhouse
        :param channel: The channel id for the active channel
        :type channel: str

        :return: Dict with information about the active channel
        :rtype: dict
        """
        def speaker_status():
            if client_info.get("is_speaker"):
                self.granted_speaker = True
                self.active_speaker = True

        def mod_status():
            if client_info.get("is_moderator"):
                self.granted_mod = True
                self.active_mod = True

        channel_info = self.get_channel(channel)
        user_info = channel_info.pop("users")
        response_dict = {"channel_info": channel_info, "user_info": user_info}

        i = 0
        for user in user_info:
            if str(user.get("user_id")) == self.client_id:
                client_info = user_info.pop(i)
                speaker_status()
                mod_status()
                response_dict["client_info"] = client_info
                break
            i += 1

        return response_dict

    def accept_speaker_invitation(self, channel):
        accepted = self.accept_speaker_invite(channel, self.client_id)
        if accepted:
            self.granted_speaker = True
            self.active_speaker = True
        return accepted

    @set_interval(10)
    def wait_speaker_permission(self, channel):
        """ (str) -> bool

        Function that runs when you've requested for a voice permission.
        """
        accept = self.accept_speaker_invitation(channel)
        if accept.get("success"):
            return False
        return True

    def reset_speaker(self, channel, interval=10, duration=120):
        logging.info("Client is no longer a speaker")

        @set_interval(interval)
        def request_rejoin():
            self.accept_speaker_invitation(channel)
            if self.granted_speaker:
                logging.info("Client accepted new speaker invitation")
                return False
            return True

        def wait_for_rejoin():
            thread = threading.Thread(target=request_rejoin)
            thread.daemon = True
            thread.start()
            # wait here for the result to be available before continuing
            thread.join(duration)

        wait_for_rejoin()
        if self.active_speaker:
            return True

    def reset_mod(self, channel, interval=10, duration=120):
        logging.info(f"Client is no longer a moderator")

        @set_interval(interval)
        def check_mod():
            self.get_channel_dict(channel)
            if self.active_speaker:
                logging.info("Client has been re-granted moderator")
                return False

            def wait_for_mod():
                thread = threading.Thread(target=check_mod)
                thread.daemon = True
                thread.start()
                # wait here for the result to be available before continuing
                thread.join(duration)

            wait_for_mod()
            if self.active_mod:
                return True

    def welcome_guests(self, channel, user_info):
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

        response = self.send_room_chat(channel, message)
        self.already_welcomed_list.append(user_info.get("user_id"))

        return response

    def invite_guests(self, channel, user_info):
        if not user_info.get("is_speaker") and not user_info.get("is_invited_as_speaker"):
            self.invite_speaker(channel, user_info.get("user_id"))
            self.welcome_guests(channel, user_info)

    def mod_guests(self, channel, user_info):
        if user_info.get("is_speaker") and not user_info.get("is_moderator"):
            self.make_moderator(channel, user_info.get("user_id"))
        if user_info.get("user_id") not in self.already_welcomed_list or self.already_in_room_list:
            self.welcome_guests(channel, user_info)













