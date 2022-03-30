#!/usr/bin/env python

# import sys
# import time
# import threading
import logging
from datetime import datetime

import pytz

from .moderator import ModClient as Mod
from .audio import AudioClient as Audio
from .chat import ChatClient as Chat


set_interval = Mod.set_interval


class AutoModClient(Mod, Audio, Chat):

    def __init__(self):
        super().__init__()

    @set_interval(180)
    def track_room_client(self, channel):
        join_dict = self.channel.join(channel)
        AutoModClient.data_dump(join_dict, 'join', channel)
        return True

    def chat_client(self, channel, chat_stream=None):
        chat_triggers = self.get_chat_stream(channel, chat_stream)
        trigger_dict = self.check_command(chat_triggers)
        self.UrbanDict.urban_dict(channel, trigger_dict)
        return True

    def speaker_status(self, client_info):
        if not client_info.get("is_speaker"):
            self.active_speaker = False
            return False
        self.active_speaker = True
        if self.waiting_speaker_thread:
            self.waiting_speaker_thread.set()
        return True

    def mod_status(self, client_info):
        if not client_info.get("is_moderator"):
            self.active_mod = False
            return False
        self.active_mod = True
        if self.waiting_mod_thread:
            self.waiting_mod_thread.set()
        return True

    def get_client_channel_status(self, channel, mod_mode=False):
        channel_dict = self.get_channel_dict(channel)
        client_info = channel_dict.get("client_info")
        is_speaker = self.speaker_status(client_info)
        is_moderator = self.mod_status(client_info)

        reset = False
        if self.granted_speaker and not is_speaker:
            logging.info("Client is no longer speaker")
            reset = self.reset_speaker(channel)
        elif mod_mode and self.granted_mod and not is_moderator:
            logging.info("Client is no longer mod")
            reset = self.reset_mod(channel)
        if not reset:
            self.terminate_channel(channel)

        return channel_dict

    @set_interval(15)
    def channel_public(self, channel):
        self.chat_client(self, channel)
        channel_dict = self.get_client_channel_status(channel, True)
        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        user_info = channel_dict.get("user_info")
        club = channel_dict.get("channel_info").get("club").get("club_id")
        for _user in user_info:
            _user_id = _user("user_id")
            if club in self.automod_clubs:
                self.invite_guests(channel, _user)
            elif self.guest_list and str(_user_id) in self.guest_list:
                self.invite_guests(channel, _user)
            if self.mod_list:
                if str(_user_id) in self.mod_list:
                    self.mod_guests(channel, _user)
        if self.dump_counter == self.dump_interval:
            self.data_dump(channel_dict, "channel_dict", channel)
            self.dump_counter = 0
        self.dump_counter += 1

    @set_interval(15)
    def channel_private_club(self, channel):
        self.chat_client(self, channel)
        channel_dict = self.get_client_channel_status(channel, True)
        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        # channel_dict = client.get_channel_dict(channel)
        user_info = channel_dict.get("user_info")
        club = str(channel_dict.get("channel_info").get("club"))
        if club in self.social_clubs:
            for _user in user_info:
                _user_id = _user("user_id")
                self.invite_guests(channel, _user)
                self.mod_guests(channel, _user)
                if _user_id not in self.already_welcomed_list and _user_id not in self.already_in_room_list:
                    self.welcome_guests(channel, _user)

        return True

    @set_interval(15)
    def channel_social_or_private(self, channel):
        self.chat_client(self, channel)
        channel_dict = self.get_client_channel_status(channel)
        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        # channel_dict = client.get_channel_dict(channel)
        user_info = channel_dict.get("user_info")

        for _user in user_info:
            _user_id = _user.get("user_id")
            if _user_id not in self.already_welcomed_list and _user_id not in self.already_in_room_list:
                self.welcome_guests(channel, _user)

    def terminate_channel(self, channel):
        self.channel.leave(channel)

        status_list = ["active_speaker", "waiting_speaker", "active_mod", "waiting_mod"]
        for status in status_list:
            if status:
                setattr(self, status, False)

        thread_list = [self.active_mod_thread, self.announcement_thread, self.music_thread, self.welcome_thread,
                       self.keep_alive_thread, self.chat_client_thread]
        for thread in thread_list:
            if thread:
                thread.set()

        self.waiting_ping_thread = self.listen_channel_ping()
        logging.info("Automation terminated")

    def init_channel(self, channel, join_info):
        if self.waiting_ping_thread:
            self.waiting_ping_thread.set()

        self.chat_client_thread = init_chat_client(channel)
        self.get_channel_dict(channel)

        join_dict = join_info
        self.waiting_speaker_thread = self.wait_speaker_permission(channel)
        self.active_ping(channel)
        self.keep_alive_thread = self.keep_alive_ping(channel)

        if join_dict.get("type") == "public":
            hello_message = self.set_hello_message(join_dict, True)
            self.send_room_chat(channel, hello_message)
            self.active_mod_thread = self.channel_public(channel)

        elif join_dict.get("type") == "private" and join_dict.get("club"):
            hello_message = self.set_hello_message(join_dict, True)
            self.send_room_chat(channel, hello_message)
            self.active_mod_thread = self.channel_private_club(channel)
            self.announcement_thread = self.set_url_announcement(channel, 120)
            # if join_dict.get("club") in client.social_clubs:
            #     client.active_mod_thread = channel_public()
            # else:
            #     client.active_mod_thread = channel_private_club()

        else:
            logging.info(f"join_dict: {join_dict}")
            hello_message = self.set_hello_message(join_dict)
            self.send_room_chat(channel, hello_message)
            self.active_mod_thread = self.channel_social_or_private(channel)

    def set_ping_responder(self, notification, _channel):

        time_created = notification.get("time_created")
        time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
        time_now = datetime.now(pytz.timezone('UTC'))
        time_diff = time_now - time_created
        time_diff = time_diff.total_seconds()

        if not time_diff <= 30:
            return False

        _user_id = str(notification.get("user_profile").get("user_id"))
        _user_name = notification.get("user_profile").get("name")
        _message = notification.get("message")

        if _channel in self.attempted_ping_response or _user_id not in self.respond_ping_list:
            logging.info("Unauthorized Ping")
            return False

        join = self.get_join_dict(_channel)
        if join.get("join_dict").get("success"):
            logging.info(f"Client pinged to {_channel} by {_user_name}: {_message}")
        else:
            self.attempted_ping_response.append(_channel)
            return False

        return join

    @set_interval(30)
    def listen_channel_ping(self):
        """
        A function listen for active ping from user on approved ping list.

        :param client: A Clubhouse object.
        :param active_mod:
        :param ping_list:
        :return decorator:
        :rtype: Dictionary
        """

        logging.info("Waiting for ping")

        # Is this active_mod check redundant?
        if self.active_mod:
            logging.info("Response: Client already active in a channel")
            return False

        respond = False
        notifications = self.get_notifications()
        if not notifications:
            return True

        for notification in notifications.get("notifications")[:5]:
            if notification.get("type") == 9:
                _channel = notification.get("channel")
                join = self.set_ping_responder(notification, _channel)

                if join:
                    # Tell client to go to channel
                    # client.active_channel = _channel
                    self.init_channel(_channel, join)
                    return False

        return True


def main(announcement=None, music=False, dump_interval=180):

    client = AutoModClient()
    client.waiting_ping_thread = client.listen_channel_ping()
    client.dump_interval = dump_interval / 15

    


