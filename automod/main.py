#!/usr/bin/env python

import sys
import logging
import time
import threading
from datetime import datetime

import pytz

from . import moderation as mod


def set_logging_config():
    config_file = "/Users/deon/Documents/GitHub/HQ/config.ini"
    config_object = mod.load_config(config_file)

    logging_config = mod.config_to_dict(config_object, "Logging")
    folder = logging_config.get("folder")
    file = logging_config.get("file")
    level = logging_config.get("level")
    filemode = logging_config.get("filemode")
    logging.basicConfig(
        filename=f"{folder}{file}",
        filemode=filemode,
        format="%(asctime)s - %(module)s - %(levelname)s - line %(lineno)d - "
               "%(funcName)s - %(message)s (Process Details: (%(process)d, "
               "%(processName)s) Thread Details: (%(thread)d, %(threadName)s))",
        datefmt="%Y-%d-%m %I:%M:%S",
        level=level)


def main(announcement=None):
    set_interval = mod.set_interval

    def set_hello_message(join_info, mod_mode=False, music=False):
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
            if mod_mode and not client.active_speaker:
                message = request_speak_and_mod()
            elif mod_mode and not client.active_mod:
                message = request_mod()
            elif music and not client.active_speaker:
                message = request_speak()
            return message

        def set_message():
            message_1 = f"🤖 Hello {join_info.get('creator')}! I'm AutoMod! 🎉"
            message_2 = map_mode()
            message = [message_1, message_2] if message_2 else [message_1]
            return message

        hello_message = set_message()

        return hello_message

    def set_url_announcement(channel, interval):
        message_1 = "The share url for this room is:"
        message_2 = f"https://www.clubhouse.com/room/{channel}"
        message = [message_1, message_2]

        client.send_room_chat(channel, message)
        response = client.set_announcement(channel, message, interval)
        return response

    def get_client_channel_status(channel, mod_mode=False):
        reset = False
        if not client.active_speaker:
            reset = client.reset_speaker(channel)
        elif mod_mode and not client.active_mod:
            reset = client.reset_mod(channel)
        if not reset:
            terminate_channel(channel)

    @set_interval(15)
    def channel_public(channel):
        get_client_channel_status(channel, True)
        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        channel_dict = client.get_channel_dict(channel)
        user_info = channel_dict.get("user_info")
        club = channel_dict.get("channel_info").get("club").get("club_id")

        for _user in user_info:
            _user_id = _user("user_id")

            if club in client.auto_mod_clubs:
                client.invite_guests(channel, _user)

            elif client.guest_list and str(_user_id) in client.guest_list:
                client.invite_guests(channel, _user)

            if client.mod_list:
                if str(_user_id) in client.mod_list:
                    client.mod_guests(channel, _user)

    @set_interval(15)
    def channel_private_club(channel):
        get_client_channel_status(channel, True)

        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        channel_dict = client.get_channel_dict(channel)
        user_info = channel_dict.get("user_info")

        for _user in user_info:
            _user_id = _user("user_id")
            client.invite_guests(channel, _user)
            client.mod_guests(channel, _user)

            if _user_id not in client.already_welcomed_list and _user_id not in client.already_in_room_list:
                client.welcome_guests(channel, _user)

        return True

    @set_interval(15)
    def channel_social_or_private(channel):
        get_client_channel_status(channel)
        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        channel_dict = client.get_channel_dict(channel)
        user_info = channel_dict.get("user_info")

        for _user in user_info:
            _user_id = _user("user_id")
            if _user_id not in client.already_welcomed_list and _user_id not in client.already_in_room_list:
                client.welcome_guests(channel, _user)

    def terminate_channel(channel):
        client.leave_channel(channel)

        client.active_speaker = False
        client.waiting_speaker = False
        client.active_mod = False
        client.waiting_mod = False

        if client.active_mod_thread:
            client.active_mod_thread.set()

        if client.announcement_thread:
            client.announcement_thread.set()

        if client.music_thread:
            client.music_thread.set()

        if client.welcome_thread:
            client.welcome_thread.set()

        if client.keep_alive_thread:
            client.keep_alive_thread.set()

        client.waiting_ping_thread = listen_channel_ping(client)

        logging.info("mAutomation terminated")

        return

    def init_channel(channel):
        client.waiting_ping_thread.set()
        join_dict = client.get_join_dict(channel)
        client.audience_reply(channel)
        client.wait_speaker_permission(channel)
        client.active_ping(channel)
        client.keep_alive_thread = client.keep_alive_ping(channel)

        if join_dict.get("type") == "public":
            hello_message = set_hello_message(join_dict, True)
            client.send_room_chat(channel, hello_message)
            client.active_mod_thread = channel_public()

        elif join_dict.get("type") == "private" and join_dict.get("club"):
            hello_message = set_hello_message(join_dict, True)
            client.send_room_chat(channel, hello_message)
            client.active_mod_thread = channel_private_club()
            client.announcement_thread = set_url_announcement(channel, 120)

        else:
            hello_message = set_hello_message(join_dict)
            client.send_room_chat(channel, hello_message)
            client.active_mod_thread = channel_social_or_private()

    def set_ping_responder(notification, _channel):
        if notification.get("type") != 9:
            return False

        _user_id = str(notification.get("user_profile").get("user_id"))
        _user_name = notification.get("user_profile")("name")

        _message = notification.get("message")

        time_created = notification.get("time_created")
        time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
        time_now = datetime.now(pytz.timezone('UTC'))
        time_diff = time_now - time_created
        time_diff = time_diff.total_seconds()

        if not time_diff <= 30 or _user_id not in client.respond_ping_list:
            return False

        logging.info(f"Client pinged to {_channel} by {_user_name}: {_message}")
        return True

    @set_interval(30)
    def listen_channel_ping():
        """
        A function listen for active ping from user on approved ping list.

        :param client: A Clubhouse object.
        :param active_mod:
        :param ping_list:
        :return decorator:
        :rtype: Dictionary
        """
        # Is this active_mod check redundant?
        if client.active_mod:
            logging.info("moderation_tools.listen_channel_ping Response: Client already active in a channel")
            return False

        notifications = client.get_notifications()
        for notification in notifications.get("notifications"):
            _channel = notification.get("channel")
            respond = set_ping_responder(notification, _channel)
            if respond:
                # Tell client to go to channel
                init_channel(_channel)
                return False

        return True

    client = mod.ModClient()
    client.waiting_ping_thread = listen_channel_ping()


if __name__ == '__main__':
    set_logging_config()
    main()
