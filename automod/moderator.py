"""
moderator.py

RTC: For voice communication
"""

import logging
import json
import time
from datetime import datetime

import pytz
import boto3

from .clubhouse import Config
from .clubhouse import Clubhouse


class ModClient(Clubhouse):
    """

    """
    set_interval = Clubhouse.set_interval

    def __init__(self):
        super().__init__()
        self.s3_bucket = Config.config_to_dict(Config.load_config(), "S3", "bucket")
        self.automod_clubs = Config.config_to_list(Config.load_config(), "AutoModClubs")
        self.social_clubs = Config.config_to_list(Config.load_config(), "SocialClubs")
        self.respond_ping_list = Config.config_to_list(Config.load_config(), "RespondPing")
        self.mod_list = Config.config_to_list(Config.load_config(), "ModList")
        self.guest_list = (Config.config_to_list(Config.load_config(), "GuestList")
                           + Config.config_to_list(Config.load_config(), "ASocialRoomGuestList"))

        self.waiting_speaker = False
        self.granted_speaker = False
        self.active_speaker = False
        self.waiting_mod = False
        self.granted_mod = False
        self.active_mod = False

        self.waiting_ping_thread = None
        self.waiting_speaker_thread = None
        self.waiting_mod_thread = None
        self.active_mod_thread = None
        self.announcement_thread = None
        self.music_thread = None
        self.welcome_thread = None
        self.keep_alive_thread = None
        self.chat_client_thread = None

        self.already_welcomed_list = []
        self.already_in_room_list = []
        self.attempted_ping_response = []

        self.dump_interval = 0
        self.dump_counter = 0

    def __str__(self):
        return f"Config: [Clubhouse User ID: {self.client_id}, [Amazon S3 Bucket: " \
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
        self.channel.active_ping(channel)
        return True

    def send_room_chat(self, channel, message=str or list):
        response = False
        if isinstance(message, str):
            message = [message]
        for item in message:
            run = self.chat.send(channel, item)
            response = run.get("success")
            time.sleep(3)
        return response

    def set_hello_message(self, join_info, mod_mode=False, music_mode=False):
        """Defines which message to send to the room chat upon joining."""
        def request_speak_and_mod():
            message = "If you'd like to use my features, please invite me to speak and make me a Moderator. ✳️"
            return message

        def request_mod():
            message = "If you'd like to use my features, please make me a Moderator. ✳️"
            return message

        def request_speak():
            message = "If you'd like to hear music, please invite me to speak. 🎶"
            return message

        def map_mode():
            message = None
            if mod_mode and not self.active_speaker:
                message = request_speak_and_mod()
            elif mod_mode and not self.active_mod:
                message = request_mod()
            elif music_mode and not self.active_speaker:
                message = request_speak()
            return message

        def set_message():
            message_1 = f"🤖 Hello {join_info.get('creator')}! I'm AutoMod! 🎉"
            message_2 = map_mode()
            message = [message_1, message_2] if message_2 else [message_1]
            return message

        hello_message = set_message()

        return hello_message

    def set_announcement(self, channel, message, interval):
        @Clubhouse.set_interval(interval)
        def announcement():
            response = self.chat.send(channel, message)
            return response
        return announcement()

    def set_url_announcement(self, channel, interval):
        message_1 = "The share url for this room is:"
        message_2 = f"https://www.clubhouse.com/room/{channel}"
        message = [message_1, message_2]
        send = self.chat.send(channel, message)
        if send.get("success"):
            response = self.set_announcement(channel, message, interval)
            return response

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
            logging.info(join_dict.get("club"))
            logging.info(join_dict.get("club").get("club_id"))
            return _club

        join_dict = self.channel.join(channel)

        response_dict = {
            "join_dict": join_dict,
            "type": channel_type(),
            "creator": channel_creator(),
            "club": club(),
        }
        return response_dict

    def get_channel_dict(self, channel):
        """Retrieves information about the active channel"""

        response_dict = {}
        channel_info = self.channel.get(channel)
        if channel_info.get("success"):
            user_info = channel_info.pop("users")
            response_dict = {"channel_info": channel_info, "user_info": user_info}

            i = 0
            for user in user_info:
                if user.get("user_id") == self.client_id:
                    client_info = user_info.pop(i)
                    response_dict["client_info"] = client_info
                    break
                i += 1

        return response_dict

    def accept_speaker_invitation(self, channel):
        accepted = self.channel.accept_speaker_invite(channel, self.client_id)
        if accepted.get("success"):
            return accepted

    @set_interval(10)
    def wait_speaker_permission(self, channel):
        accept = self.accept_speaker_invitation(channel)
        if not accept.get("success"):
            return True

    def reset_speaker(self, channel, interval=10, duration=120):
        _range = duration // interval
        logging.info("Client is no longer a speaker")
        logging.info("checking for speaker rejoin")
        self.channel.audience_reply()
        time.sleep(5)
        for attempts in range(_range):
            attempt = self.accept_speaker_invitation(channel)
            if not attempt.get("success"):
                time.sleep(interval)
            else:
                return True
        channel_dict = self.get_channel_dict(channel)
        if channel_dict.get("client_info").get("is_speaker"):
            logging.info("Client accepted new speaker invitation")
            return True

    def reset_mod(self, channel, interval=10, duration=120):
        _range = duration // interval
        logging.info(f"Client is no longer a moderator")
        logging.info("checking for speaker rejoin")
        for attempts in range(_range):
            channel_dict = self.get_channel_dict(channel)
            if not channel_dict.get("client_info").get("is_moderator"):
                time.sleep(interval)
            else:
                logging.info("Client has been re-granted moderator")
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

        response = self.chat.send(channel, message)
        self.already_welcomed_list.append(user_info.get("user_id"))

        return response

    def invite_guests(self, channel, user_info):
        if not user_info.get("is_speaker") and not user_info.get("is_invited_as_speaker"):
            self.mod.invite_speaker(channel, user_info.get("user_id"))
            self.welcome_guests(channel, user_info)

    def mod_guests(self, channel, user_info):
        if user_info.get("is_speaker") and not user_info.get("is_moderator"):
            self.mod.make_moderator(channel, user_info.get("user_id"))
        if user_info.get("user_id") not in self.already_welcomed_list or self.already_in_room_list:
            self.welcome_guests(channel, user_info)













