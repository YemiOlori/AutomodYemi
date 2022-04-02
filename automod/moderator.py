"""
moderator.py

RTC: For voice communication
"""

import logging
import threading
import json
import time
from datetime import datetime
from datetime import timedelta

import pytz
import boto3

from .clubhouse import Config
from .clubhouse import Clubhouse


class ModClient(Clubhouse):
    set_interval = Clubhouse.set_interval

    # Should I add phone number and verification code to __init__?
    # Add pickling to save data in case client refreshes before channel ends
    def __init__(self):
        super().__init__()

        self.config = Config.load_config()
        self.automod_clubs = Config.config_to_list(Config.load_config(), "AutoModClubs", True)
        self.social_clubs = Config.config_to_list(Config.load_config(), "SocialClubs", True)
        # self.respond_ping_list = Config.config_to_list(Config.load_config(), "RespondPing", True)
        self.mod_list = Config.config_to_list(Config.load_config(), "ModList", True)
        self.guest_list = (Config.config_to_list(Config.load_config(), "GuestList", True)
                           + Config.config_to_list(Config.load_config(), "ASocialRoomGuestList", True))

        self.waiting_speaker = False
        self.granted_speaker = False
        self.active_speaker = False
        self.waiting_mod = False
        self.granted_mod = False
        self.active_mod = False

        self.url_announcement = False
        self.in_automod_club = False
        self.in_social_club = False

        self.public_channel = False
        self.private_channel = False
        self.social_channel = False
        self.club_id = False

        # self.waiting_ping_thread = None
        self.waiting_speaker_thread = None
        self.waiting_mod_thread = None
        self.active_mod_thread = None
        self.announcement_thread = None
        # self.music_thread = None
        self.welcome_thread = None
        self.keep_alive_thread = None
        self.chat_client_thread = None

        self.already_welcomed_set = []
        self.already_in_room_set = []
        # self.attempted_ping_response = []

        self.dump_interval = 0
        self.dump_counter = 0


    def __str__(self):
        return f"Config: [Clubhouse User ID: {self.client_id}]"

    def get_join_dict(self, channel):
        join_info = self._get_join_info(channel)
        if not join_info:
            return

        elif not join_info.get("success"):
            return

        channel_type = self._get_channel_type(join_info)
        host_name = self._get_host_name(join_info)
        club_id = self._get_club(join_info)
        chat_enabled = self._get_chat_info(join_info)
        auto_speaker_approval = self._get_auto_speaker_approval(join_info)
        channel_url = self._get_url(join_info)
        time_message = self._get_time_created(join_info)
        users_in_room = self._get_users_in_room(join_info)
        token = self._get_token(join_info)

        join_dict = {
            "channel_type": channel_type,
            "host_name": host_name,
            "club_id": club_id,
            "chat_enabled": chat_enabled,
            "auto_speaker_approval": auto_speaker_approval,
            "channel_url": channel_url,
            "time_message": time_message,
            "users_in_room": users_in_room,
            "token": token,
        }
        return join_dict

    def _get_join_info(self, channel):
        join_info = self.channel.join_channel(channel)
        return join_info

    def _get_channel_type(self, join_info):
        _type = "public"

        if join_info.get("is_private"):
            _type = "private"
            self.private_channel = True

        elif join_info.get("is_social_mode"):
            _type = "social"
            self.social_channel = False

        else:
            self.public_channel = True

        logging.info(_type)
        return _type

    @staticmethod
    def _get_host_name(join_info):

        creator_id = join_info.get("creator_user_profile_id")
        name = [user["first_name"] for user in join_info.get("users") if user["user_id"] == creator_id][0]

        if not name:
            name = join_info.get("users")[0].get("first_name")

        logging.info(name)
        return name

    def _get_club(self, join_info):
        _club = join_info.get("club")

        if not _club:
            return

        _club_id = _club.get("club_id")
        self.club_id = _club_id

        logging.info(_club_id)
        return _club_id

    @staticmethod
    def _get_chat_info(join_or_channel_info):
        chat_enabled = join_or_channel_info.get("is_chat_enabled")

        logging.info(chat_enabled)
        return chat_enabled

    @staticmethod
    def _get_auto_speaker_approval(join_info):
        auto_speaker_approval = join_info.get("is_automatic_speaker_approval_available")

        logging.info(auto_speaker_approval)
        return auto_speaker_approval

    @staticmethod
    def _get_url(join_info):
        # May not need this function
        # Can generate url from channel id
        _url = join_info.get("url")

        if _url:
            _url = _url.split("?")[0]

        logging.info(_url)
        return _url

    @staticmethod
    def _get_time_created(join_info):
        pubnub_time_token = join_info.get("pubnub_time_token")

        # See pubnub documentation https://www.pubnub.com/docs/sdks/python/api-reference/misc
        time_created = datetime.fromtimestamp(pubnub_time_token / 10000000)
        eastern_time = time_created + timedelta(hours=1)
        # [Shrugs] Because the world runs on Eastern Standard time...
        time_message = eastern_time.strftime("This room was created on %m/%d/%Y at %-I:%M:%S %p ET")

        logging.info(time_message)
        return time_message

    def _get_users_in_room(self, join_info):
        users = join_info.get("users")
        self.already_in_room_set = set(user.get("user_id") for user in users)
        return users

    @staticmethod
    def _get_token(join_dict):
        # For audio client
        token = join_dict.get("token")

        logging.info(token)
        return token

    def _get_channel_info(self, channel):
        channel_info = self.channel.get_channel(channel)
        return channel_info

    def _get_user_and_client_info(self, channel_dict):
        user_info = channel_dict.get("users")

        i = 0
        for user in user_info:
            if user.get("user_id") == self.client_id:
                client_info = user_info.pop(i)

                logging.info(client_info)
                return user_info, client_info

            i += 1

    def get_channel_dict(self, channel):
        channel_dict = self._get_channel_info(channel)
        if not channel_dict:
            return

        elif not channel_dict.get("success"):
            return

        user_dict, client_dict = self._get_user_and_client_info(channel_dict)
        is_speaker = client_dict.get("is_speaker")
        is_moderator = client_dict.get("is_moderator")
        chat_enabled = self._get_chat_info(channel_dict)

        channel_dict = {
            "user_dict": user_dict,
            "is_speaker": is_speaker,
            "is_mod": is_moderator,
            "chat_enabled": chat_enabled,
        }
        return channel_dict

    def _get_speaker_status(self, channel):
        channel_dict = self.get_channel_dict(channel)
        is_speaker = channel_dict.get("is_speaker")

        if is_speaker:
            self.waiting_speaker = False
            self.active_speaker = True

        logging.info(is_speaker)
        return is_speaker

    def _get_mod_status(self, channel):
        channel_dict = self.get_channel_dict(channel)
        is_moderator = channel_dict.get("is_mod")

        if is_moderator:
            self.waiting_mod = False
            self.active_mod = True

        logging.info(is_moderator)
        return is_moderator

    def _set_init_status(self, join_dict, channel_dict):

        if join_dict.get("auto_speaker_approval"):
            self.active_speaker = True

        elif channel_dict.get("is_mod"):
            self.granted_speaker = True
            self.active_speaker = True
            self.granted_mod = True
            self.active_mod = True

        elif channel_dict.get("is_speaker"):
            self.waiting_mod = True
            self.granted_speaker = True
            self.active_speaker = True

        else:
            self.waiting_speaker = True

        if self.club_id:

            if self.private_channel:
                self.url_announcement = True

            if self.club_id in self.automod_clubs:
                self.in_automod_club = True

            if self.club_id in self.social_clubs:
                self.in_social_club = True

        for user in join_dict.get("users_in_room"):
            _user_id = user.get("user_id")
            self.already_in_room_set.append(_user_id)

    @staticmethod
    def _request_speak_and_mod_message():
        message = "If you'd like to use my features, please invite me to speak and make me a Moderator. ✳️"
        return message

    @staticmethod
    def _request_mod_message():
        message = "If you'd like to use my features, please make me a Moderator. ✳️"
        return message

    @staticmethod
    def _request_speak_message():
        message = "If you'd like to hear music, please invite me to speak. 🎶"
        return message


    def _check_speaker_status(self, channel, interval, active_speaker_status):

        while not active_speaker_status.isSet():
            self.channel.accept_speaker_invite(channel, self.client_id)
            self.granted_speaker = self._get_speaker_status(channel)

            if self.granted_speaker:
                active_speaker_status.set()
                self.waiting_speaker = False
                self.active_speaker = True
                logging.info(f"Stopped: {self.waiting_speaker_thread}")

            else:
                logging.info("Still waiting to join stage")

            active_speaker_status.wait(interval)

    def wait_to_speak(self, channel, channel_dict, interval=10, duration=120):
        self.granted_speaker = self._get_speaker_status(channel)
        if self.granted_speaker:
            self.waiting_speaker = False
            self.active_speaker = True
            return True

        active_speaker_status = threading.Event()
        self.waiting_speaker_thread = threading.Thread(
            target=self._check_speaker_status, args=(self, channel, interval, channel_dict, active_speaker_status,))

        self.waiting_speaker_thread.daemon = True
        self.waiting_speaker_thread.start()
        self.waiting_speaker_thread.join(duration)
        logging.info(f"Stopped: {self.waiting_speaker_thread}")

        if self.active_speaker:
            return True

    def _check_mod_status(self, channel, interval, active_mod_status):

        while not active_mod_status.isSet():
            self.granted_mod = self._get_mod_status(channel)

            if self.granted_mod:
                active_mod_status.set()
                self.waiting_mod = False
                self.active_mod = True
                logging.info(f"Stopped: {self.waiting_mod_thread}")

            else:
                logging.info("Still waiting mod privileges")

            active_mod_status.wait(interval)

    def wait_for_mod(self, channel, channel_dict, interval=10, duration=120):
        self.granted_mod = self._get_mod_status(channel)
        if self.granted_mod:
            self.waiting_mod = False
            self.active_mod = True
            return True

        active_mod_status = threading.Event()
        self.waiting_mod_thread = threading.Thread(
            target=self._check_mod_status, args=(self, channel, interval, channel_dict, active_mod_status))

        self.waiting_mod_thread.daemon = True
        self.waiting_mod_thread.start()
        self.waiting_mod_thread.join(duration)
        logging.info(f"Started: {self.waiting_mod_thread}")

        if self.active_mod:
            return True

    @staticmethod
    def confirm_channel_init(join_dict, channel_dict):
        if not join_dict:
            return

        elif not join_dict.get("success"):
            return

        elif not channel_dict:
            return

        elif not channel_dict.get("success"):
            return

        return True

    @set_interval(30)
    def keep_alive_ping(self, channel):
        self.channel.active_ping(channel)
        return True

    @staticmethod
    def set_url_announcement(channel):

        message_1 = "The share url for this room is:"
        message_2 = f"https://www.clubhouse.com/room/{channel}"
        message = [message_1, message_2]

        return message

    def set_announcement(self, channel, message, interval, delay=None):
        send = self.chat.send_chat(channel, message)
        if not send.get("success"):
            return

        @self.set_interval(interval * 60)
        def announcement():
            response = self.send_room_chat(channel, message, delay)
            return response

        return announcement()

    def init_channel(self, channel, join_dict, channel_dict=None, api_retry_interval_sec=30, duration=120,
                     announcement=None, announcement_interval_min=60, announcement_delay=None):

        if not channel_dict:
            channel_dict = self.get_channel_dict(channel)

        confirm = self.confirm_channel_init(join_dict, channel_dict)
        if not confirm:
            return

        self.keep_alive_thread = self.keep_alive_ping(channel)

        self._set_init_status(join_dict, channel_dict)

        if join_dict.get("chat_enabled"):
            targeted_message = self._set_targeted_message()
            hello_message = self.set_hello_message(join_dict, targeted_message)
            say_hello = self.send_room_chat(join_dict, hello_message, delay=0)
            logging.info(say_hello)

        if self.waiting_speaker:
            raise_hand = self.channel.audience_reply(channel)
            if not raise_hand.get("success"):
                return

            self.wait_to_speak(channel, channel_dict, api_retry_interval_sec, duration)

            if not self.active_speaker:
                return

        if self.waiting_mod:
            self.wait_for_mod(channel, channel_dict, api_retry_interval_sec, duration)

            if not self.active_mod:
                return

        if join_dict.get("chat_enabled"):

            if self.url_announcement and not announcement:
                announcement = self.set_url_announcement(channel)
                announcement_interval_min = 60
                announcement_delay = 10

            if announcement:
                self.announcement_thread = self.set_announcement(
                    channel, announcement, announcement_interval_min, announcement_delay)

    @staticmethod
    def welcome_message(first_name, user_id):
        name = first_name
        message = f"Welcome {name}! 🎉"

        if user_id == 2350087:
            message = f"Welcome Disco Doggie! 🎉"

        elif user_id == 1414736198:
            message = "Tabi! Hello my love! 😍"

        elif user_id == 47107:
            message_2 = "Ryan, please don't choose violence today!"
            message = [message, message_2]

        elif user_id == 2247221:
            message_2 = "First"
            message_3 = "And furthermore, infinitesimal"
            message = [message, message_2, message_3]

        return message

    def invite_guests(self, channel, user_info, guest_list=False):
        if not user_info:
            return

        user_id = user_info.get("user_id")

        if guest_list and user_id not in self.guest_list:
            return

        is_speaker = user_info.get("is_speaker")
        is_invited_as_speaker = user_info.get("is_invited_as_speaker")
        first_name = user_info.get("first_name")
        welcome_message = self.welcome_message(first_name, user_id)

        if is_speaker or is_invited_as_speaker:
            return

        else:
            invite = self.channel.invite_speaker(channel, user_id)
            send = self.send_room_chat(channel, welcome_message, delay=2)
            if not invite and not send:
                return
            self.already_welcomed_set.append(user_id)

        if user_id not in self.already_welcomed_set and user_id not in self.already_in_room_set:
            send = self.send_room_chat(channel, welcome_message, delay=2)
            if not send:
                return
            self.already_welcomed_set.append(user_id)

        return True

    def mod_guests(self, channel, user_info, mod_list=False):
        if not user_info:
            return

        user_id = user_info.get("user_id")

        if mod_list and user_id not in self.mod_list:
            return

        is_speaker = user_info.get("is_speaker")
        is_mod = user_info.get("is_mod")

        if is_speaker and not is_mod:
            self.mod.make_moderator(channel, user_info.get("user_id"))

        if user_id not in self.already_welcomed_set or self.already_in_room_set:
            first_name = user_info.get("first_name")
            welcome_message = self.welcome_message(first_name, user_id)
            send = self.send_room_chat(channel, welcome_message, delay=2)
            self.welcome_guests(channel, user_info)





















































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

















