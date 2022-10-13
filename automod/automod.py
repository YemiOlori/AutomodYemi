import logging
import pytz

from datetime import datetime

from automod.logger import Logger
from automod.moderator import ModClient
from automod.moderator import TrenchClient
from automod.chat import ChatClient as Chat
from automod.audio import AudioClient as Audio

set_interval = ModClient.set_interval


class AutoModClient(ModClient, Chat, Audio):
	
	def __init__(self):
		super().__init__()
		# Logger()
		logging.info("Initializing AutoModClient...")
		self.channel_id = 0
		
		self.automod_active = False
		self.chat_active = False
		self.respond = False
		self.joined_channel = False
		self.channel_status = False
		self.notification = {}
		self.join_info = {}
		
		self.ping_responded_set = set()
		self.scanned_notifications_set = set()
		
		self.waiting_ping_thread = None
		self.active_channel_thread = None
		self.chat_client_thread = None
		self.welcome_client_thread = None
		
		self.chat_counter = 0
		self.dump_counter = 0
		
		self.user_group = ""
	
	def run_automod(self, interval=300):
		self.automod_active = False
		self.waiting_ping_thread = self.listen_for_ping(interval)
	
	@set_interval(30)
	def listen_for_ping(self, interval=300):
		
		logging.info("Waiting for ping")
		notifications = self.notifications.get_notifications()
		if not notifications:
			return True
		
		notifications = notifications and [_ for _ in notifications.get("notifications")[:10] if _.get("type") == 9]
		
		for notification in notifications:
			logging.info(f"Notification: {notification}")
			self.notification = notification
			logging.info(f"Notification: {self.notification}")
			if self.notification.get("notification_id") in self.scanned_notifications_set:
				logging.info(f"Notification already scanned: {self.notification}")
				continue
			
			self.ping_responder(interval)
			if self.joined_channel:
				return False
		
		return True
	
	def ping_responder(self, interval=300):
		time_created = datetime.strptime(self.notification.get("time_created"), '%Y-%m-%dT%H:%M:%S.%f%z')
		time_now = datetime.now(pytz.timezone('UTC'))
		time_diff = (time_now - time_created).total_seconds()
		
		if time_diff > interval:
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			return
		
		logging.info(f"Notification: {self.notification}")
		
		if self.notification.get("user_profile").get("user_id") not in self.ping_response_set:
			logging.info(f"Ping from unauthorized user: {self.notification.get('message')}")
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			return
		
		if self.notification.get("channel") in self.ping_responded_set:
			logging.info(
				f"Already attempted to respond to a ping from this channel: {self.notification.get('message')}")
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			return
		
		logging.info(
			f"Client pinged to {self.notification.get('channel')} by "
			f"{self.notification.get('user_profile').get('name')}: {self.notification.get('message')}")
		
		joined = self.automod_init()
		if joined:
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			self.ping_responded_set.add(self.notification.get("channel"))
			self.waiting_ping_thread.set() if self.waiting_ping_thread else None
	
	def automod_init(
			self, channel=0, api_retry_interval_sec=10, thread_timeout=120,
			announcement=None, announcement_interval_min=60, announcement_delay=0,
			audio=False):
		
		self.channel_id = channel or self.notification.get("channel")
		
		self.join_info = self.channel_init(
			self.channel_id, api_retry_interval_sec, thread_timeout, announcement,
			announcement_interval_min, announcement_delay)
		
		if self.join_info is False:
			self.ping_responded_set.add(self.channel_id)
			return
		
		elif not self.join_info:
			return
		
		elif self.join_info.get("success") is False:
			logging.info(self.join_info)
			
			if "That room is no longer available" in self.join_info.get("error_message"):
				self.ping_responded_set.add(self.channel_id)
				self.scanned_notifications_set.add(self.notification.get("notification_id"))
				logging.info("Channel is closed")
			return
		
		if self.waiting_ping_thread:
			logging.info("Waiting for ping thread to finish - automod_init")
			self.waiting_ping_thread.set()
		
		self.active_channel_thread = self.active_channel_init()
		self.chat_client_thread = self.chat_client_init(self.channel_id)
		# self.welcome_client_thread = self.welcome_client_init()
		self.automod_active = True
		self.ping_responded_set.add(self.channel_id)
		self.scanned_notifications_set.add(self.channel_id)
		logging.info(f"Scanned notifications: {self.scanned_notifications_set}")
		
		if audio:
			self.start_audio(channel, self.join_info.get("token"))
			self.unmute_audio()
		
		return self.join_info
	
	@set_interval(20)
	def chat_client_init(self, channel, response_interval=300, response_delay=10):
		if not self.chat_active:
			return True
		self.run_chat_client(channel, response_interval, response_delay)
		return True
	
	@set_interval(15)
	def active_channel_init(
			self, message_delay=2, reconnect_interval=10, reconnect_timeout=120, dump_interval=16):
		
		channel_info = self.confirm_active_channel(
			self.channel_id, message_delay, reconnect_interval, reconnect_timeout)
		
		if not channel_info:
			self.automod_active = False
			self.waiting_ping_thread = self.listen_for_ping()
			self.terminate_channel_init()
			return
		
		self.chat_active = self.set_chat_enabled(channel_info=channel_info)
		
		return True
	
	@set_interval(20)
	def welcome_client_init(self, message_delay=5):
		user_info = self.set_users_info()
		if not user_info:
			return True
		
		self.welcome_guests(message_delay)
		return True
	
	def terminate_channel_init(self):
		
		self.terminate_channel()
		self.active_channel_thread = self.active_channel_thread.set() if self.active_channel_thread else None
		self.chat_client_thread = self.chat_client_thread.set() if self.chat_client_thread else None
		self.welcome_client_thread = self.welcome_client_thread.set() if self.welcome_client_thread else None
		
		self.terminate_music(self.channel_id)
		self.terminate_chat_client()


class TrenchesAutoModClient(TrenchClient, Chat, Audio):
	def __init__(self, account, config):
		super().__init__(account, config)
		# Logger()
		logging.info("Initializing AutoModClient...")
		self.channel_id = 0
		self.account = account
		self.config = config
		
		self.automod_active = False
		self.chat_active = False
		self.respond = False
		self.joined_channel = False
		self.channel_status = False
		self.notification = {}
		self.join_info = {}
		
		self.ping_responded_set = set()
		self.scanned_notifications_set = set()
		
		self.waiting_ping_thread = None
		self.active_channel_thread = None
		self.chat_client_thread = None
		self.welcome_client_thread = None
		
		self.chat_counter = 0
		self.dump_counter = 0
	
	def run_automod(self, interval=300):
		self.automod_active = False
		self.waiting_ping_thread = self.listen_for_ping(interval)
	
	@set_interval(30)
	def listen_for_ping(self, interval=300):
		
		logging.info("Waiting for ping")
		notifications = self.notifications.get_notifications()
		if not notifications or not notifications.get("notifications"):
			return True
		
		num = min(len(notifications.get("notifications")), 10)
		notifications = [_ for _ in notifications.get("notifications")[:num] if _.get("type") == 9 and _.get("notification_id") not in self.scanned_notifications_set]
		
		for notification in notifications:
			self.notification = notification
			logging.info(f"Notification: {notification}")
			self.ping_responder(interval)
			if self.joined_channel:
				return False
		
		return True
	
	def ping_responder(self, interval=300):
		time_created = datetime.strptime(self.notification.get("time_created"), '%Y-%m-%dT%H:%M:%S.%f%z')
		time_now = datetime.now(pytz.timezone('UTC'))
		time_diff = (time_now - time_created).total_seconds()
		
		if time_diff > interval:
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			return
		
		if self.notification.get("user_profile").get("user_id") not in self.ping_response_set:
			logging.info(f"Ping from unauthorized user: {self.notification.get('message')}")
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			return
		
		# Change this to not retry only if room was closed
		if self.notification.get("channel") in self.ping_responded_set:
			logging.info(
				f"Already attempted to respond to a ping from this channel: {self.notification.get('message')}")
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			return
		
		logging.info(
			f"Client pinged to {self.notification.get('channel')} by "
			f"{self.notification.get('user_profile').get('name')}: {self.notification.get('message')}")
		
		joined = self.automod_init()
		if joined:
			self.scanned_notifications_set.add(self.notification.get("notification_id"))
			self.ping_responded_set.add(self.notification.get("channel"))
	
	def automod_init(
			self, channel=0, api_retry_interval_sec=10, thread_timeout=120,
			announcement=None, announcement_interval_min=20, announcement_delay=0,
			audio=False):
		
		announcement = announcement
		
		self.channel_id = channel or self.notification.get("channel")
		
		self.join_info = self.channel_init(
			self.channel_id, api_retry_interval_sec, thread_timeout, announcement,
			announcement_interval_min, announcement_delay)
		
		if self.join_info is False:
			self.ping_responded_set.add(self.channel_id)
			return
		
		elif not self.join_info:
			return
		
		elif self.join_info.get("success") is False:
			logging.info(self.join_info)
			
			if "That room is no longer available" in self.join_info.get("error_message"):
				self.ping_responded_set.add(self.channel_id)
				self.scanned_notifications_set.add(self.notification.get("notification_id"))
				logging.info("Channel is closed")
			return
		
		if self.waiting_ping_thread:
			logging.info("Waiting for ping thread to finish - automod_init")
			self.waiting_ping_thread.set()
		
		self.active_channel_thread = self.active_channel_init()
		self.chat_client_thread = self.chat_client_init(self.channel_id)
		# self.welcome_client_thread = self.welcome_client_init()
		self.automod_active = True
		self.ping_responded_set.add(self.channel_id)
		self.scanned_notifications_set.add(self.channel_id)
		logging.info(f"Scanned notifications: {self.scanned_notifications_set}")
		
		if audio:
			self.start_audio(channel, self.join_info.get("token"))
			self.unmute_audio()
		
		return self.join_info
	
	@set_interval(15)
	def active_channel_init(
			self, message_delay=2, reconnect_interval=10, reconnect_timeout=120, dump_interval=16):
		
		channel_info = self.confirm_active_channel(
			self.channel_id, message_delay, reconnect_interval, reconnect_timeout)
		
		if not channel_info:
			self.automod_active = False
			self.waiting_ping_thread = self.listen_for_ping()
			self.terminate_channel_init()
			return
		
		self.chat_active = self.set_chat_enabled(channel_info=channel_info)
		
		return True
	
	@set_interval(15)
	def chat_client_init(self, channel, response_interval=300, response_delay=5):
		if not self.chat_active:
			return True
		self.run_chat_client(channel, response_interval, response_delay)
		return True
	
	@set_interval(20)
	def welcome_client_init(self, message_delay=5):
		user_info = self.get_users_info()
		if not user_info:
			return True
		self.welcome_guests(message_delay)
		return True
	
	def terminate_channel_init(self, audio=False):
		self.terminate_channel_mod()
		if audio:
			self.terminate_music(self.channel_id)
			
		self.active_channel_thread = self.active_channel_thread.set() if self.active_channel_thread else None
		self.chat_client_thread = self.chat_client_thread.set() if self.chat_client_thread else None
		self.welcome_client_thread = self.welcome_client_thread.set() if self.welcome_client_thread else None


def run_automod_client(interval=300):
	AutoModClient().run_automod(interval)


if __name__ == "__main__":
	run_automod_client(interval=300)
