#!/usr/bin/env python

import logging
from datetime import datetime
import pytz

# import sys
# sys.path.append('/Users/deon/Documents/GitHub_local/am_local_2')

from automod.moderator import ModClient as Mod
from automod.chat import ChatClient as Chat
from automod.audio import AudioClient as Audio
from automod.tracker import Tracker
from automod.logger import Logger


set_interval = Mod.set_interval


def run_automod_client(interval=300):
    AutoModClient().run_automod(interval)


# noinspection DuplicatedCode
class AutoModClient(Mod, Chat, Audio, Tracker):

    def __init__(self):
        super().__init__()
        
        logger = Logger()
        logger.run_logger()
        logging.info("API Configuration Loaded")

    def run_automod(self, interval=300):
        self.automod_active = False
        self.waiting_ping_thread = self.listen_for_ping(interval)

    @set_interval(30)
    def listen_for_ping(self, interval=300, dump_interval=4):
        logging.info("Waiting for ping")

        notifications = self.notifications.get_notifications()
        if not notifications:
            return True

        for notification in notifications.get("notifications")[:10]:
            notification_id = notification.get("notification_id")
            notification_type = notification.get("type")

            if notification_id in self.scanned_notifications_set or notification_type != 9:
                self.scanned_notifications_set.add(notification_id)
                continue

            respond = self.ping_responder(notification, notification_id, interval)
            if respond:
                return False

        if self.dump_counter == dump_interval:
            self.dump_counter = 0

            feed_info = self.client.feed()
            if feed_info:
                if feed_info.get("items"):
                    self.data_dump(feed_info, "feed")

        self.dump_counter += 1

        return True

    def ping_responder(self, notification, notification_id, interval=300):
        time_created = notification.get("time_created")
        time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
        time_now = datetime.now(pytz.timezone('UTC'))
        time_diff = time_now - time_created
        time_diff = time_diff.total_seconds()

        if time_diff > interval:
            self.scanned_notifications_set.add(notification_id)
            return

        logging.info(notification)
        user_id = notification.get("user_profile").get("user_id")
        message = notification.get("message")

        if user_id not in self.ping_response_set:
            logging.info(f"Ping from unauthorized user: {message}")
            self.scanned_notifications_set.add(notification_id)
            return

        channel = notification.get("channel")
        if channel in self.ping_responded_set:
            logging.info(f"Already attempted to respond to a ping from this channel: {message}")
            self.scanned_notifications_set.add(notification_id)
            return

        user_name = notification.get("user_profile").get("name")
        logging.info(f"Client pinged to {channel} by {user_name}: {message}")

        join = self.automod_init(channel, notification_id)
        if join:
            self.scanned_notifications_set.add(notification_id)

        return join

    def automod_init(
            self, channel, notification_id=None, api_retry_interval_sec=10, thread_timeout=120,
            announcement=None, announcement_interval_min=60, announcement_delay=None):

        join_info = self.channel_init(
            channel, api_retry_interval_sec, thread_timeout, announcement, announcement_interval_min,
            announcement_delay)

        if join_info is False:
            self.ping_responded_set.add(channel)
            return

        elif not join_info:
            return

        elif join_info.get("success") is False:
            logging.info(join_info)

            error_message = join_info.get("error_message")
            if "That room is no longer available" in error_message:
                self.ping_responded_set.add(channel)
                self.scanned_notifications_set.add(notification_id)
                logging.info("Channel is closed")
            return

        if self.waiting_ping_thread:
            self.waiting_ping_thread.set()

        self.active_channel_thread = self.active_channel_init(channel)
        self.chat_client_thread = self.chat_client_init(channel)
        self.welcome_client_thread = self.welcome_client_init(channel)
        self.automod_active = True
        self.ping_responded_set.add(channel)
        self.scanned_notifications_set.add(notification_id)
        logging.info(f"Scanned notifications: {self.scanned_notifications_set}")

        if not join_info.get("is_private") and not join_info.get("is_social_mode"):
            self.data_dump(join_info, "join", channel)

        return True

    @set_interval(15)
    def active_channel_init(
            self, channel, message_delay=2, reconnect_interval=10, reconnect_timeout=120, dump_interval=16):

        channel_info = self.active_channel(channel, message_delay, reconnect_interval, reconnect_timeout)

        if not channel_info:
            self.automod_active = False
            self.waiting_ping_thread = self.listen_for_ping()
            self.terminate_channel_init(channel)
            return

        self.chat_active = self.get_chat_enabled(channel_info)

        if self.dump_counter == dump_interval:
            self.dump_counter = 0

            feed_info = self.client.feed()
            if feed_info:
                if feed_info.get("items"):
                    self.data_dump(feed_info, "feed")

            if not channel_info.get("is_private") and not channel_info.get("is_social_mode"):
                self.data_dump(channel_info, "channel", channel)

        self.dump_counter += 1

        return True

    @set_interval(20)
    def chat_client_init(self, channel, response_interval=300, response_delay=10):
        if not self.chat_active:
            return True
        self.run_chat_client(channel, response_interval, response_delay)
        return True

    @set_interval(20)
    def welcome_client_init(self, channel, message_delay=5):
        user_info = self.get_users_info(channel)
        if not user_info:
            return True
        self.welcome_guests(channel, user_info, message_delay)
        return True

    def terminate_channel_init(self, channel):

        self.terminate_channel(channel)

        if self.active_channel_thread:
            self.active_channel_thread.set()

        if self.chat_client_thread:
            self.chat_client_thread.set()

        if self.welcome_client_thread:
            self.welcome_client_thread.set()


    automod_active = None
    chat_active = None

    ping_responded_set = set()
    scanned_notifications_set = set()

    waiting_ping_thread = None
    active_channel_thread = None
    chat_client_thread = None
    welcome_client_thread = None

    chat_counter = 0
    dump_counter = 0


if __name__ == "__main__":
    run_automod_client(interval=300)


