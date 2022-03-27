#!/usr/bin/env python

import sys
import logging
from datetime import datetime

import pytz

from .clubhouse import Clubhouse
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


def main():
    set_interval = mod.set_interval

    @set_interval(15)
    def mod_client():
        channel_dict = client.get_channel_status(channel)
        channel_info = channel_dict.get("channel_info")
        user_info = channel_dict["user_info"]

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
                logging.info("moderation_tools.mod_channel ModClient is no longer a speaker")
                logging.info("moderation_tools.mod_channel ModClient attempted to accept new speaker invitation")

                if client_speaker_status:
                    logging.info("moderation_tools.mod_channel ModClient accepted new speaker invitation")

            elif Var.active_mod and not client_mod_status and not social_mode and Var.counter == 4:
                logging.info(f"moderation_tools.mod_channel ModClient is not a moderator")
                Var.waiting_mod = True

            if Var.waiting_mod and not client_mod_status and not social_mode and Var.counter == 3:
                termination(client, channel)
                logging.info("moderation_tools.mod_channel Triggered terminate_mod")
                return False

            try:
                channel_info['club']
            except KeyError:
                logging.info("NO CLUB")
                club = False
            else:
                club = channel_info['club']['club_id']

            Var.active_mod = True

            for _user in user_info:
                user_id = _user['user_id']

                if private:
                    if client_mod_status:
                        invite_guests(client, channel, _user)
                        mod_guests(client, channel, _user)

                elif club == 863466177 or club == 313157294:
                    invite_guests(client, channel, _user)

                    if client_mod_status and Var.mod_list:
                        if str(user_id) in Var.mod_list:
                            mod_guests(client, channel, _user)

                else:
                    if client_mod_status and Var.guest_list:
                        if str(user_id) in Var.guest_list:
                            invite_guests(client, channel, _user)

                    if client_mod_status and Var.mod_list:
                        if str(user_id) in Var.mod_list:
                            mod_guests(client, channel, _user)

                if social_mode or private:
                    if user_id not in Var.already_welcomed_list and user_id not in Var.already_in_room_list:
                        welcome_guests(client, channel, _user)

            if not social_mode and not private and not club and Var.counter == 4:
                feed_info = client.get_feed()
                data_dump(feed_info, 'feed')
                data_dump(channel_dict, 'channel_dict', channel)

            Var.counter += 1

        return True







    def set_notification_responder(notification, _channel):
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
            respond = set_notification_responder(notification, _channel)
            if respond:
                # Tell client to go to channel
                automation(client, _channel, "mod", )
                logging.info("moderation_tools.listen_channel_ping Triggered active_mod_channel")
                return False

        return True

    channel = "None"
    client = mod.ModClient()
    client.waiting_ping_thread = listen_channel_ping()

    join_dict = client.get_join_status(channel)


















def scratch():

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

    def say_hello(client, join_dict, channel_dict, mod_channel=False, music=False):
        channel = channel_dict.get("channel")
        message = set_hello_message(join_dict, channel_dict, mod_channel, music)
        run = send_room_chat(client, channel, message)
        response = run.get("success")
        return response

    def say_hello(client, channel, message):
        response = client.send_room_chat(channel, message)
        return response

















if __name__ == '__main__':
    set_logging_config()
    main()