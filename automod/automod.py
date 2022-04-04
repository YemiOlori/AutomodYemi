#!/usr/bin/env python

from .moderator import ModClient as Mod
from .audio import AudioClient as Audio
from .chat import ChatClient as Chat

set_interval = Mod.set_interval


class AutoModClient(Mod, Chat, Audio):

    def __init__(self):
        super().__init__()


    def run_automod(self, channel, api_retry_interval_sec=10, thread_timeout=120,
                    announcement=None, announcement_interval_min=60, announcement_delay=None):

        # Start ChatClient
        # Start TrackerClient
        # Add Timestamp Announcement

        join_info, channel_info, users_info, client_info = \
            self.channel_init(channel, api_retry_interval_sec, thread_timeout,
                              announcement, announcement_interval_min, announcement_delay)

        self.active_mod_thread = self.init_active_channel(channel)

        if self.get_chat_enabled(channel_info):
            self.chat_client_thread = self.init_chat_client(channel)


    @set_interval(30)
    def init_chat_client(self, channel, response_interval=120, delay=10):
        self.run_chat_client(channel, response_interval, delay)
        return True

    @set_interval(15)
    def init_active_channel(self, channel, message_delay=2):
        self.active_channel(channel, message_delay)
        return True



    waiting_ping_thread = None
    active_mod_thread = None
    chat_client_thread = None
