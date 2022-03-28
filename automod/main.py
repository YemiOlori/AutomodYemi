#!/usr/bin/env python

import sys
import logging
import time
import threading
from datetime import datetime

import pytz

from . import moderation as mod
from .chat import chat_client

from . import logger

logger.set_logging_config()
# Create a logger object.

set_interval = mod.set_interval


@set_interval(180)
def track_room_client(client, channel):
    join_dict = client.join_channel(channel)
    mod.ModClient.data_dump(join_dict, 'join', channel)
    return True


def main(announcement=None, music=False, dump_interval=180):

    def speaker_status(client_info):
        if not client_info.get("is_speaker"):
            client.active_speaker = False
            return False
        client.active_speaker = True
        if client.waiting_speaker_thread:
            client.waiting_speaker_thread.set()
        return True

    def mod_status(client_info):
        if not client_info.get("is_moderator"):
            client.active_mod = False
            return False
        client.active_mod = True
        if client.waiting_mod_thread:
            client.waiting_mod_thread.set()
        return True

    def get_client_channel_status(channel, mod_mode=False):
        channel_dict = client.get_channel_dict(channel)
        client_info = channel_dict.get("client_info")

        is_speaker = speaker_status(client_info)
        is_moderator = mod_status(client_info)

        reset = False
        if client.granted_speaker and not is_speaker:
            logging.info("Client is no longer speaker")
            reset = client.reset_speaker(channel)

        elif mod_mode and client.granted_mod and not is_moderator:
            logging.info("Client is no longer mod")
            reset = client.reset_mod(channel)

        if not reset:
            terminate_channel(channel)

        return channel_dict

    @set_interval(15)
    def channel_public(channel):
        channel_dict = get_client_channel_status(channel, True)
        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
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

        if client.dump_counter == client.dump_interval:
            client.data_dump(channel_dict, "channel_dict", channel)
            client.dump_counter = 0

        client.dump_counter += 1

    @set_interval(15)
    def channel_private_club(channel):
        channel_dict = get_client_channel_status(channel, True)

        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        # channel_dict = client.get_channel_dict(channel)
        user_info = channel_dict.get("user_info")
        club = str(channel_dict.get("channel_info").get("club"))

        if club in client.social_clubs:

            for _user in user_info:
                _user_id = _user("user_id")
                client.invite_guests(channel, _user)
                client.mod_guests(channel, _user)

                if _user_id not in client.already_welcomed_list and _user_id not in client.already_in_room_list:
                    client.welcome_guests(channel, _user)

        return True

    @set_interval(15)
    def channel_social_or_private(channel):
        channel_dict = get_client_channel_status(channel)
        # Make sure that client is active speaker before running this function
        # Make sure that client is active mod before running this function
        # channel_dict = client.get_channel_dict(channel)
        user_info = channel_dict.get("user_info")

        for _user in user_info:
            _user_id = _user.get("user_id")
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

        if client.chat_client_thread:
            client.chat_client_thread.set()

        client.waiting_ping_thread = listen_channel_ping()

        logging.info("Automation terminated")

        return

    @set_interval(20)
    def init_chat_client(channel):
        chat_client(channel)
        return True

    def init_channel(channel, join_info):
        if client.waiting_ping_thread:
            client.waiting_ping_thread.set()

        client.chat_client_thread = init_chat_client(channel)
        client.get_channel_dict(channel)

        join_dict = join_info
        client.waiting_speaker_thread = client.wait_speaker_permission(channel)
        client.active_ping(channel)
        client.keep_alive_thread = client.keep_alive_ping(channel)

        if join_dict.get("type") == "public":
            hello_message = set_hello_message(join_dict, True)
            client.send_room_chat(channel, hello_message)
            client.active_mod_thread = channel_public(channel)

        elif join_dict.get("type") == "private" and join_dict.get("club"):
            hello_message = set_hello_message(join_dict, True)
            client.send_room_chat(channel, hello_message)
            client.active_mod_thread = channel_private_club(channel)
            client.announcement_thread = set_url_announcement(channel, 120)
            # if join_dict.get("club") in client.social_clubs:
            #     client.active_mod_thread = channel_public()
            # else:
            #     client.active_mod_thread = channel_private_club()

        else:
            logging.info(f"join_dict: {join_dict}")
            hello_message = set_hello_message(join_dict)
            client.send_room_chat(channel, hello_message)
            client.active_mod_thread = channel_social_or_private(channel)

    def set_ping_responder(notification, _channel):

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

        if _channel in client.attempted_ping_response or _user_id not in client.respond_ping_list:
            logging.info("Unauthorized Ping")
            return False

        join = client.get_join_dict(_channel)
        if join.get("join_dict").get("success"):
            logging.info(f"Client pinged to {_channel} by {_user_name}: {_message}")
        else:
            client.attempted_ping_response.append(_channel)
            return False

        return join

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

        logging.info("Waiting for ping")

        # Is this active_mod check redundant?
        if client.active_mod:
            logging.info("Response: Client already active in a channel")
            return False

        respond = False
        notifications = client.get_notifications()
        if not notifications:
            return True

        for notification in notifications.get("notifications")[:5]:
            if notification.get("type") == 9:
                _channel = notification.get("channel")
                join = set_ping_responder(notification, _channel)

                if join:
                    # Tell client to go to channel
                    # client.active_channel = _channel
                    init_channel(_channel, join)
                    return False

        return True

    client = mod.ModClient()
    # client = mod.reload_user()
    client.waiting_ping_thread = listen_channel_ping()
    client.dump_interval = dump_interval / 15

    


