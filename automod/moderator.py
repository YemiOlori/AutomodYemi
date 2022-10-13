import logging
import threading
import random
import pytz

from datetime import datetime
from datetime import timezone
from time import sleep

from .clubhouse import Config
from .clubhouse import Clubhouse

set_interval = Clubhouse.set_interval


class ModClient(Clubhouse):
    def __init__(self):
        super().__init__()
        logging.info("Initializing ModClient...")
        
        self.channel_id = 0
        self.join_info = {}
        self.channel_info = {}
        self.users_info = {}
        self.client_info = {}
        
        self.targeted_message = ""
        self.hello_message = ""
        self.hello_message_alt = ""
        
        self.channel_url = ""
        self.host_info = {}
        self.host_name = ""
        self.host_id = 0
        self.creator_id = 0
        self.channel_type = ""
        self.club_id = 0
        self.chat_enabled = False
        self.auto_speaker_approval = False
        self.time_created = ""
        self.token = ""

        self.channel_active = False
        self.waiting_speaker = False
        self.granted_speaker = False
        self.active_speaker = False
        self.waiting_mod = False
        self.granted_mod = False
        self.active_mod = False

        self.already_in_room_set = set()
        self.screened_user_set = set()
        self.unscreened_user_set = set()
        self.screened_for_speaker_set = set()
        self.screened_for_mod_set = set()
        self.already_welcomed_set = set()
        self.filtered_users_list = []

        self.url_announcement = False
        self.in_automod_club = False
        self.in_social_club = False
        self.in_wwsl_club = False

        self.waiting_speaker_thread = None
        self.waiting_mod_thread = None
        self.waiting_reconnect_thread = None

        self.announcement_thread = None
        self.url_announcement_thread = None
        self.runtime_announcement_thread = None
        self.music_thread = None
        self.welcome_thread = None
        self.keep_alive_thread = None
        self.chat_client_thread = None
        
        self.automod_clubs = set(Config.config_to_list(Config.load_config(), "AutoModClubs", True))
        self.social_clubs = set(Config.config_to_list(Config.load_config(), "SocialClubs", True))
        self.wwsl_club = Config.config_to_dict(Config.load_config(), "Clubs", "wwsl")
        self.ping_response_set = set(Config.config_to_list(Config.load_config(), "RespondPing", True))
        self.mod_list = set(
            (Config.config_to_list(Config.load_config(), "ModList", True)
             + Config.config_to_list(Config.load_config(), "TrenchesModList", True)))
        self.guest_list = set(
            (Config.config_to_list(Config.load_config(), "GuestList", True)
             + Config.config_to_list(Config.load_config(), "ASocialRoomGuestList", True)
             + Config.config_to_list(Config.load_config(), "TrenchesModList", True)
             + Config.config_to_list(Config.load_config(), "TrenchesGuestList", True)))
        self.trenches_ping = set(Config.config_to_list(Config.load_config(), "TrenchesPing", True))

        # self.trenches_mod_list = set(Config.config_to_list(Config.load_config(), "TrenchesModList", True))
        # self.trenches_guest_list = (set(
        #     Config.config_to_list(Config.load_config(), "TrenchesModList", True) +
        #     Config.config_to_list(Config.load_config(), "TrenchesGuestList", True)))

    def channel_init(self, channel, ping_id=0, api_retry_interval_sec=10, thread_timeout=120,
                     announcement="", announcement_interval_min=60, announcement_delay=0):
        
        self.channel_id = channel
        self.channel_url = f"https://www.clubhouse.com/room/{self.channel_id}"
        logging.info("Initializing channel checkpoint 1...")

        # set join status
        self.get_join_info()
        
        if not self.join_info or not self.join_info.get("success"):
            logging.info(f"Did not successfully join channel: {channel}")
            return False
        
        self.set_channel_type()
        self.set_host()
        self.set_club_id()
        self.set_auto_speaker_approval()
        self.set_time_created()
        self.set_token()
        self.set_screened_users()
        self.set_chat_enabled(on_join=True)
        logging.info("Initializing channel checkpoint 2...")

        self.already_welcomed_set.add(self.host_id)
        self.already_welcomed_set.add(self.client_id)
        
        # set channel status
        self.get_channel_info()
        logging.info("Initializing channel checkpoint 3...")
        
        if not self.channel_info or not self.channel_info.get("success"):
            self.channel_active = False
            logging.info(f"No longer connected to channel: {channel}")
            return False
        else:
            self.channel_active = True

        self.set_users_info()
        self.set_client_info()
        self.filter_screened_users() # Do I need this?
        self.set_speaker_status()
        self.set_mod_status()
        logging.info("Initializing channel checkpoint 4...")
        
        # channel init
        self.set_channel_init()
        self.keep_alive_thread = self.keep_alive_ping()

        self.set_targeted_message()
        self.set_hello_message()
        # self.send_hello_message() if self.chat_enabled else None
        logging.info("Initializing channel checkpoint 5...")

        self.wait_to_speak(api_retry_interval_sec, thread_timeout) if self.waiting_speaker else None
        if self.waiting_speaker and not self.active_speaker:
            logging.info("Client was not invited as speaker")
            self.terminate_channel()
            return False
        
        logging.info("Initializing channel checkpoint 6...")
        
        self.wait_for_mod(api_retry_interval_sec, thread_timeout) if self.waiting_mod else None
        if self.waiting_mod and not self.active_mod:
            logging.info("Client was not given moderator privileges")
            self.terminate_channel()
            return False
        
        if self.chat_enabled and self.url_announcement:
            self.url_announcement_thread = self.set_url_announcement()
            self.runtime_announcement_thread = self.set_runtime_announcement()

        if self.chat_enabled and announcement:
            self.announcement_thread = self.set_announcement(
                announcement, announcement_interval_min, announcement_delay)
            
        return self.join_info
            
    def confirm_active_channel(
            self, channel, message_delay=2, reconnect_interval=10, reconnect_timeout=120):
        
        self.channel_id = channel

        self.refresh_channel_status()

        if not self.channel_active:
            logging.info(f"Attempting to reconnect: {channel}")
            is_active = self.wait_for_reconnection(reconnect_interval, reconnect_timeout)

            if not is_active:
                logging.info("Unable to reconnect. Terminating channel...")
                self.terminate_channel()
                return

        if self.granted_speaker and not self.active_speaker:
            logging.info(f"Attempting to rejoin as speaker: {channel}")
            is_speaker = self.wait_to_speak(reconnect_interval, reconnect_timeout)

            if not is_speaker:
                logging.info("Unable to rejoin as speaker. Terminating channel...")
                self.terminate_channel()
                return

        if self.granted_mod and not self.active_mod:
            logging.info(f"Attempting to rejoin as mod: {channel}")
            is_mod = self.wait_to_speak(reconnect_interval, reconnect_timeout)

            if not is_mod:
                logging.info("Unable to rejoin as mod. Terminating channel...")
                self.terminate_channel()
                return

        if self.channel_type != "public" or self.in_wwsl_club or self.in_automod_club or self.in_social_club:
            self.welcome_guests(message_delay=5)

        if self.users_info:
            self.invite_guests(message_delay)
            self.mod_guests()

        return self.channel_info
    
    # ----------------- ENTER CHANNEL ----------------- #
    def get_join_info(self):
        self.join_info = self.channel.join_channel(self.channel_id)
        return self.join_info
    
    def set_channel_type(self, on_join=True):
        if on_join:
            self.channel_type = (
                "lounge" if self.join_info.get("is_social_club_lounge") else
                "social" if self.join_info.get("is_social_mode") else
                "private" if self.join_info.get("is_private") else
                "public")
            return self.channel_type

    def set_host(self):
        self.creator_id = self.join_info.get("creator_user_profile_id")
        logging.info(f"Creator ID: {self.creator_id}")
        
        host_info = [_ for _ in self.join_info.get("users") if _.get("user_id") == self.creator_id]
        self.host_info = host_info[0] if host_info else self.join_info.get("users")[0]
        host_name = [_.get("first_name") for _ in self.join_info.get("users") if _.get("user_id") == self.creator_id]
    
        if host_name:
            logging.info(f"Creator Name: {self.creator_id}")
            self.host_id = self.creator_id
            self.host_name = host_name[0]
    
        else:
            self.host_name = self.host_info.get("first_name")
            self.host_id = self.host_info.get("user_id")
    
        logging.info(f"Host: {self.host_name}")
    
    def set_club_id(self):
        self.club_id = self.join_info.get("club").get("club_id") if self.join_info.get("club") else 0
        logging.info(f"Club: {self.club_id}")

    def set_auto_speaker_approval(self):
        self.auto_speaker_approval = self.join_info.get("is_automatic_speaker_approval_available")
        logging.info(f"Auto Speaker Approval: {self.auto_speaker_approval}")
    
        if self.auto_speaker_approval:
            self.channel.accept_speaker_invite(self.channel_id, self.client_id)
            self.channel.become_speaker(self.channel_id)
    
    def set_time_created(self):

        first_speaker = [_ for _ in self.join_info.get("users") if _.get("is_speaker") and not _.get("is_moderator")]
        first_speaker = first_speaker[0] if first_speaker else self.host_info

        host_time = self.host_info.get("time_joined_as_speaker")
        host_time = host_time and datetime.strptime(host_time, "%Y-%m-%dT%H:%M:%S.%f%z")

        first_speaker_time = first_speaker.get("time_joined_as_speaker")
        first_speaker_time = (
                first_speaker_time and host_time and datetime.strptime(first_speaker_time, "%Y-%m-%dT%H:%M:%S.%f%z"))

        earliest_recorded_time = first_speaker_time and min(host_time, first_speaker_time)
        earliest_recorded_time = earliest_recorded_time or datetime.now(timezone.utc)
        # tz_aware = pytz.timezone('US/Eastern').localize(eastern_time)

        self.time_created = earliest_recorded_time
        logging.info(f"Earliest Recorded Time: {self.time_created}")

    def set_token(self):
        self.token = self.join_info.get("token")  # For audio client
        logging.info(f"Token: {self.token}")

    def set_screened_users(self):
        users = self.join_info.get("users")
        self.screened_user_set = set(_.get("user_id") for _ in users)
        self.already_in_room_set = self.screened_user_set
        self.screened_user_set.add(self.client_id)

    def set_chat_enabled(self, on_join=False, channel_info=None):
    
        if on_join:
            self.chat_enabled = self.join_info.get("is_chat_enabled")
            return self.chat_enabled
    
        elif channel_info:
            self.chat_enabled = channel_info.get("is_chat_enabled")
            return self.chat_enabled
    
        self.chat_enabled = self.channel_info.get("is_chat_enabled")
        logging.info(f"Chat Enabled: {self.chat_enabled}")

    # ----------------- CONFIG CHANNEL INIT ----------------- #
    def set_channel_init(self):
        # Set waiting_mod and waiting_speaker statuses
        if not self.auto_speaker_approval and not self.active_speaker:
            self.waiting_mod = True
            self.waiting_speaker = True

        elif (self.channel_type == "public" or self.club_id) and not self.active_mod:
            self.waiting_mod = True
            self.waiting_speaker = False

        # Set url_announcement status
        if self.channel_type == "private":
            self.url_announcement = True

        # Set in_automod_club status
        if str(self.club_id) in self.automod_clubs:
            self.in_automod_club = True

        # Set in_social_club status
        elif str(self.club_id) in self.social_clubs:
            self.in_social_club = True

        elif str(self.club_id) in self.wwsl_club:
            self.in_wwsl_club = True
            
    def get_channel_info(self):
        self.channel_info = self.channel.get_channel(self.channel_id)

    def set_users_info(self):
        self.users_info = self.channel_info.get("users")
        return self.users_info

    def set_client_info(self):
        self.client_info = [_ for _ in self.users_info if _.get("user_id") == self.client_id][0]

    def set_speaker_status(self):
        self.active_speaker = self.client_info.get("is_speaker")
    
        if self.active_speaker:
            self.granted_speaker = True
            self.waiting_speaker = False

    def set_mod_status(self):
        self.active_mod = self.client_info.get("is_moderator")
    
        if self.active_mod:
            self.granted_mod = True
            self.waiting_mod = False

    def filter_screened_users(self, for_speaker=False, for_mod=False):
    
        if for_speaker:
            self.filtered_users_list = [_ for _ in self.users_info
                                        if _.get("user_id") not in self.screened_for_speaker_set]
    
        elif for_mod:
            self.filtered_users_list = [_ for _ in self.users_info if _.get("user_id") not in self.screened_for_mod_set]
    
        else:
            self.filtered_users_list = [_ for _ in self.users_info if _.get("user_id") not in self.screened_user_set]
    
        return self.filtered_users_list
    
    def set_runtime_message(self):
        current_time = datetime.now(tz=pytz.UTC)
        running_time = current_time - self.time_created
        time_string = str(running_time).split(".")[0]

        message = f"This room has been running for {time_string}."
        logging.info(message)

        return message

    @staticmethod
    def request_speak_and_mod_message():
        message_1 = "If you'd like to use my features, please invite me to speak and make me a Moderator. ✳️"
        message_2 = "✳️ Please invite me to speak and make me a Moderator if you'd like to use my features!"
        return message_1, message_2

    @staticmethod
    def request_mod_message():
        message_1 = "If you'd like to use my features, please make me a Moderator. ✳️"
        message_2 = "✳️ Please make me a Moderator if you'd like to use my features!️"
        return message_1, message_2

    @staticmethod
    def request_speak_message():
        message_1 = "If you'd like to hear music, please invite me to speak. 🎶"
        message_2 = "Please invite me to speak if you'd like to hear music!"
        return message_1, message_2

    # ----------------- CHANNEL INIT ----------------- #

    @set_interval(30)
    def keep_alive_ping(self):
        self.channel.active_ping(self.channel_id)
        return True
     
    def set_targeted_message(self):

        if self.waiting_speaker and self.waiting_mod:
            self.targeted_message = self.request_speak_and_mod_message()

        elif self.waiting_mod:
            self.targeted_message = self.request_mod_message()

        elif self.waiting_speaker:
            self.targeted_message = self.request_speak_message()

        else:
            self.targeted_message = ""
            
    def set_hello_message(self):

        self.hello_message = f"🤖 Hello {self.host_name}! I'm {self.client_name}! 🎉 "
        self.hello_message_alt = f"🤖 Hey {self.host_name}! {self.client_name}, here! 🎉 "

        if isinstance(self.targeted_message, str):
            self.hello_message = [self.hello_message + self.targeted_message]

        elif isinstance(self.targeted_message, list):
            self.hello_message = [self.hello_message] + self.targeted_message

        if isinstance(self.targeted_message, tuple):
            self.hello_message = [self.hello_message + self.targeted_message[0]]
            self.hello_message_alt = [self.hello_message_alt + self.targeted_message[1]]

    def send_hello_message(self, delay=5):
        response = False
    
        send = self.send_room_chat(self.hello_message, delay)
        logging.info(f"Hello Message: {send}")
    
        if send.get("success") is not False:
            return send.get("success")
    
        error_message = send.get("error_message")
        if "something like that" in error_message:
            response = self.send_room_chat(self.hello_message_alt, delay)
            logging.info(f"Sent alternate hello message: {self.hello_message_alt}")
            logging.info(response)
    
        return response

    def wait_to_speak(self, interval=5, timeout=120):
        self.channel.audience_reply(self.channel_id)
    
        active_speaker_status = threading.Event()
        self.waiting_speaker_thread = threading.Thread(
            target=self.recheck_speaker_status, args=(interval, active_speaker_status))
    
        self.waiting_speaker_thread.daemon = True
        self.waiting_speaker_thread.start()
        logging.info(f"Started: {self.waiting_speaker_thread}")
        self.waiting_speaker_thread.join(timeout)
        logging.info(f"Joined: {self.waiting_speaker_thread}")
        active_speaker_status.set()
    
        return True if self.active_speaker else False

    def recheck_speaker_status(self, interval, active_speaker_status):
    
        while not active_speaker_status.isSet():
            self.channel.accept_speaker_invite(self.channel_id, self.client_id)
            self.channel.become_speaker(self.channel_id)
            self.reset_client_status()
        
            if self.granted_speaker:
                active_speaker_status.set()
                logging.info(f"Stopped: {self.waiting_speaker_thread}")
        
            else:
                logging.info("Still waiting to join stage")
        
            active_speaker_status.wait(interval)

    def wait_for_mod(self, interval=5, timeout=120):
    
        active_mod_status = threading.Event()
        self.waiting_mod_thread = threading.Thread(
            target=self.recheck_mod_status, args=(interval, active_mod_status))
    
        self.waiting_mod_thread.daemon = True
        self.waiting_mod_thread.start()
        logging.info(f"Started: {self.waiting_mod_thread}")
        self.waiting_mod_thread.join(timeout)
        logging.info(f"Joined: {self.waiting_mod_thread}")
        active_mod_status.set()
    
        return True if self.active_mod else False

    def recheck_mod_status(self, interval, active_mod_status):
    
        while not active_mod_status.isSet():
            self.reset_client_status()
        
            if self.granted_mod:
                active_mod_status.set()
                logging.info(f"Stopped: {self.waiting_mod_thread}")
        
            else:
                logging.info("Still waiting mod privileges")
        
            active_mod_status.wait(interval)

    def set_url_announcement(self, interval=60, delay=2):
        message_1 = "The share url for this room is:"
        # message_2 = f"https://www.clubhouse.com/room/{self.channel}"
        message_2 = self.channel_url
        message = [message_1, message_2]
    
        self.send_room_chat(message, delay)
    
        @self.set_interval(interval * 60)
        def announcement():
            response = self.send_room_chat(message, delay)
            response = response.get("success")
            return response
    
        return announcement()

    def set_runtime_announcement(self, interval=30, delay=2):
        message = self.set_runtime_message()
        self.send_room_chat(message, delay)
    
        @self.set_interval(interval * 60)
        def announcement():
            message_current = self.set_runtime_message()
            response = self.send_room_chat(message_current, delay)
            response = response.get("success")
            return response
    
        return announcement()

    def set_announcement(self, message, interval, delay=None):
    
        @self.set_interval(interval * 60)
        def announcement():
            response = self.send_room_chat(message, delay)
            response = response.get("success")
            return response
    
        return announcement()

    # ----------------- RUN AUTOMOD ----------------- #

    def reset_client_status(self):
        self.get_channel_info()
        if not self.channel_info or not self.channel_info.get("success"):
            return
    
        self.set_users_info()
        self.set_client_info()
        self.set_speaker_status()
        self.set_mod_status()
    
    def refresh_channel_status(self):
        self.reset_client_status()

        if not self.channel_info or not self.channel_info.get("success"):
            self.channel_active = False
            return {}, {}, {}

        self.set_chat_enabled()

        return self.channel_info, self.users_info, self.client_info
    
    def set_welcome_message(self, first_name, user_id):
        if user_id == 2350087:
            first_name = "Disco Doggie"

        name = first_name
        message = f"Welcome {name}! 🎉"

        if user_id == 1414736198:
            message = "Tabi! Hello my love! 😍"

        elif user_id == 47107:
            message_2 = "Ryan, please don't choose violence today!"
            message = [message, message_2]

        elif user_id == 2247221:
            message_2 = "First"
            message_3 = "And furthermore, infinitesimal"
            message = [message, message_2, message_3]

        elif user_id in self.already_in_room_set:
            message_1 = f"Nice to see you {name}! 🎉"
            message_2 = f"Heeeeey {name}! 🥳"
            message_3 = f"¡Hola {name}! 🎊"

            options = [message_1, message_2, message_3]
            message = random.choice(options)

        return message

    def welcome_guests(self, message_delay=5):

        for user in self.users_info:
            welcome_message = self.set_welcome_message(user.get("first_name"), user.get("user_id"))
            welcome = False

            if ((self.in_automod_club or self.in_social_club or self.in_wwsl_club) and
                    user.get("user_id") not in self.already_welcomed_set):
                
                logging.info(welcome_message)
                welcome = self.send_room_chat(welcome_message, message_delay)

            elif (user.get("user_id") not in self.already_welcomed_set and
                  user.get("user_id") not in self.screened_user_set):
                
                logging.info(welcome_message)
                welcome = self.send_room_chat(welcome_message, message_delay)

            if welcome and welcome.get("success") is False:
                error_message = welcome.get("error_message")
                logging.info(error_message)
                if "Less is more" in error_message:
                    sleep(30)
                    break
                
                self.already_welcomed_set.add(user.get("user_id"))

        sleep(message_delay)

    def invite_guests(self, message_delay=2):

        if not self.in_automod_club and not self.in_social_club:
            users = self.filter_screened_users(for_speaker=True)
        else:
            users = self.users_info

        for user in users:
            welcome_message = self.set_welcome_message(user.get("first_name"), user.get("user_id"))

            if user.get("user_id") in self.guest_list or self.in_automod_club or self.in_social_club:

                if not user.get("is_speaker") and not user.get("is_invited_as_speaker"):
                    self.mod.invite_speaker(self.channel_id, user.get("user_id"))
                    send = self.send_room_chat(welcome_message, message_delay)
                    
                    if send.get("success"):
                        self.already_welcomed_set.add(user.get("user_id"))

            self.screened_for_speaker_set.add(user.get("user_id"))
            
        # owner_id_list = [27813, 2350087]
        # owner_invite = (
        #     True if len([user for user in self.users_info if user.get("user_id") in owner_id_list]) > 0 else False)
        #
        # if not owner_invite:
        #     return True
        #
        # for owner in owner_id_list:
        #     if
        #     self.mod.invite_speaker(self.channel_id, self.client_id)
        #     self.send_room_chat(welcome_message, message_delay)
        #     self.already_welcomed_set.add(self.client_id)

        sleep(message_delay)
        
        return True

    def mod_guests(self):

        if not self.in_social_club:
            self.filter_screened_users(for_mod=True)
            logging.info(f"Filtered users for mod: {self.filtered_users_list}")

        for user in self.filtered_users_list:
            if ((user.get("user_id") in self.mod_list or self.in_social_club) and
                    (user.get("is_speaker") and not user.get("is_moderator"))):

                self.mod.make_moderator(self.channel_id, user.get("user_id"))
                logging.info(f"Attempted to make {user.get('first_name')} a moderator")

            self.screened_for_mod_set.add(user.get("user_id"))

    def send_room_chat(self, message, delay=10):
        response = {"success": False, "error_message": "internal response - send_room_chat"}
        message = [message] if isinstance(message, str) else message
    
        for _ in message:
            response = self.chat.send_chat(self.channel_id, _)
            sleep(delay)
    
        return response

    def wait_for_reconnection(self, interval=20, timeout=120):
    
        active_channel_status = threading.Event()
        self.waiting_reconnect_thread = threading.Thread(
            target=self.recheck_connection_status, args=(interval, active_channel_status))
    
        self.waiting_reconnect_thread.daemon = True
        self.waiting_reconnect_thread.start()
        logging.info(f"Started: {self.waiting_reconnect_thread}")
        self.waiting_reconnect_thread.join(timeout)
        logging.info(f"Joined: {self.waiting_reconnect_thread}")
    
        return True if self.channel_active else False

    def recheck_connection_status(self, interval, active_channel_status):
    
        while not active_channel_status.isSet():
            join = self.channel.join_channel(self.channel_id)
            if join and join.get("success"):
                self.channel_active = True
            
            elif join and join.get("success") is False:
                logging.info(join)
                
                if "That room is no longer available" in join.get("error_message"):
                    active_channel_status.set()
                    logging.info("Channel is closed")
                    logging.info(f"Stopped: {self.waiting_reconnect_thread}")
        
            if self.channel_active:
                active_channel_status.set()
                logging.info(f"Stopped: {self.waiting_reconnect_thread}")
            else:
                logging.info("Still attempting to reconnect")
        
            active_channel_status.wait(interval)

    def terminate_channel(self):
        self.channel.leave_channel(self.channel_id)
    
        if self.keep_alive_thread:
            self.keep_alive_thread.set()
    
        if self.announcement_thread:
            self.announcement_thread.set()
    
        self.channel_id = 0
        self.join_info = {}
        self.channel_info = {}
        self.users_info = {}
        self.client_info = {}
    
        self.targeted_message = ""
        self.hello_message = ""
        self.hello_message_alt = ""
    
        self.channel_url = ""
        self.host_info = {}
        self.host_name = ""
        self.host_id = 0
        self.creator_id = 0
        self.channel_type = ""
        self.club_id = 0
        self.chat_enabled = False
        self.auto_speaker_approval = False
        self.time_created = ""
        self.token = ""
    
        self.channel_active = False
        self.waiting_speaker = False
        self.granted_speaker = False
        self.active_speaker = False
        self.waiting_mod = False
        self.granted_mod = False
        self.active_mod = False
    
        self.screened_user_set = set()
        self.unscreened_user_set = set()
        self.screened_for_speaker_set = set()
        self.screened_for_mod_set = set()
        self.already_welcomed_set = set()
        self.filtered_users_list = []
    
        self.url_announcement = False
        self.in_automod_club = False
        self.in_social_club = False
        self.in_wwsl_club = False


class TrenchClient(Clubhouse):
    def __init__(self, account, config):
        super().__init__(account, config)
        logging.info("Initializing ModClient...")
        
        self.channel_id = 0
        self.join_info = {}
        self.channel_info = {}
        self.users_info = {}
        self.client_info = {}
        
        self.targeted_message = ""
        self.hello_message = ""
        self.hello_message_alt = ""
        
        self.channel_url = ""
        self.host_info = {}
        self.host_name = ""
        self.host_id = 0
        self.creator_id = 0
        self.channel_type = ""
        self.club_id = 0
        self.chat_enabled = False
        self.auto_speaker_approval = False
        self.time_created = ""
        self.token = ""
        
        self.channel_active = False
        self.waiting_speaker = False
        self.granted_speaker = False
        self.active_speaker = False
        self.waiting_mod = False
        self.granted_mod = False
        self.active_mod = False
        
        self.already_in_room_set = set()
        self.screened_user_set = set()
        self.unscreened_user_set = set()
        self.screened_for_speaker_set = set()
        self.screened_for_mod_set = set()
        self.already_welcomed_set = set()
        self.filtered_users_list = []
        
        self.has_shared_room = set()
        self.has_shared_room.add(self.client_id)
        self.share_cursors = set()
        self.share_ids = set()
        
        self.url_announcement = False
        
        self.waiting_speaker_thread = None
        self.waiting_mod_thread = None
        self.waiting_reconnect_thread = None
        
        self.announcement_thread = None
        self.url_announcement_thread = None
        self.runtime_announcement_thread = None
        self.music_thread = None
        self.welcome_thread = None
        self.keep_alive_thread = None
        self.chat_client_thread = None
        
        self.ping_response_set = set(self.config_to_list(self.load_config(), "RespondPing", True))
        self.mod_list = set(self.config_to_list(self.load_config(), "ModList", True))
        self.vip_list = set(self.config_to_list(self.load_config(), "VIPList", True))
        self.guest_list = set(self.config_to_list(self.load_config(), "GuestList", True))
        self.remove_list = set(self.config_to_list(self.load_config(), "RemoveList", True))

        self.welcome_msg = self.config_to_dict(self.load_config(), "CustomWelcome")
    
    def channel_init(
            self, channel, api_retry_interval_sec=5, thread_timeout=300,
            announcement="", announcement_interval_min=60, announcement_delay=0):
        
        self.channel_id = channel
        self.channel_url = f"https://www.clubhouse.com/room/{self.channel_id}"
        
        # set join status
        self.get_join_info()
        if not self.join_info or not self.join_info.get("success"):
            logging.info(f"Did not successfully join channel: {channel}")
            return False
        
        # become speaker and moderator
        self.set_auto_speaker_approval()
        
        self.get_channel_info()
        self.get_users_info()
        self.get_client_info()
        self.set_client_status()
        
        if not self.active_speaker:
            self.attempt_active_speaker()
            self.wait_to_speak(api_retry_interval_sec, thread_timeout)
            if not self.active_speaker:
                logging.info("Client was not invited as speaker")
                self.terminate_channel_mod()
                return False
        
        # if not self.active_mod:
        #     self.wait_for_mod(api_retry_interval_sec, thread_timeout)
        #     if not self.active_mod:
        #         logging.info("Client was not made a moderator")
        #         self.terminate_channel_mod()
        #         return False
        
        self.keep_alive_thread = self.keep_alive_ping()
        
        self.set_host()
        self.set_club_id()
        self.set_time_created()
        self.set_token()
        self.set_users_already_in_room()
        self.set_chat_enabled(on_join=True)
        
        if self.chat_enabled:
            self.send_hello_message()
        
        if announcement:
            self.announcement_thread = self.set_announcement(
                announcement, announcement_interval_min, announcement_delay)
        
        self.already_welcomed_set.add(self.client_id)
        self.already_welcomed_set.add(self.host_id)
        
        return self.join_info
    
    def confirm_active_channel(
            self, channel, message_delay=2, reconnect_interval=5, reconnect_timeout=300):
        
        self.channel_id = channel
        self.refresh_channel_status()
        
        if not self.channel_active:
            logging.info(f"Attempting to reconnect: {channel}")
            is_active = self.wait_for_reconnection(reconnect_interval, reconnect_timeout)
            
            if not is_active:
                logging.info("Unable to reconnect. Terminating channel...")
                self.terminate_channel_mod()
                return
        
        if not self.active_speaker:
            logging.info(f"Attempting to rejoin as speaker: {channel}")
            is_speaker = self.wait_to_speak(reconnect_interval, reconnect_timeout)
            
            if not is_speaker:
                logging.info("Unable to rejoin as speaker. Terminating channel...")
                self.terminate_channel_mod()
                return
        
        if self.users_info and self.active_mod:
            self.invite_guests(message_delay)
            self.mod_guests()

        self.get_all_shares()
            
        return self.channel_info
    
    # ----------------- Get Join/Channel Info ----------------- #
    def get_join_info(self):
        self.join_info = self.channel.join_channel(self.channel_id)
        return self.join_info
    
    def get_channel_info(self):
        self.channel_info = self.channel.get_channel(self.channel_id)
    
    def get_users_info(self):
        self.users_info = self.channel_info.get("users")
        return self.users_info
    
    def get_client_info(self):
        self.client_info = [_ for _ in self.users_info if _.get("user_id") == self.client_id]
        self.client_info = self.client_info[0] if self.client_info else None
        return self.client_info
    
    # ----------------- Channel Settings ----------------- #
    def set_auto_speaker_approval(self):
        self.auto_speaker_approval = self.join_info.get("is_automatic_speaker_approval_available")
        logging.info(f"Auto Speaker Approval: {self.auto_speaker_approval}")
    
    def set_host(self):
        self.creator_id = self.join_info.get("creator_user_profile_id")
        host_info = [_ for _ in self.join_info.get("users") if _.get("user_id") == self.creator_id]
        self.host_info = host_info[0] if host_info else self.join_info.get("users")[1]
        self.host_name = self.host_info.get("first_name")
        self.host_id = self.host_info.get("user_id")
        
        logging.info(f"Host: {self.host_name}")
    
    def set_club_id(self):
        self.club_id = self.join_info.get("club").get("club_id") if self.join_info.get("club") else 0
        logging.info(f"Club: {self.club_id}")
    
    def set_time_created(self):
        
        first_speaker = [
            _ for _ in self.join_info.get("users")
            if _.get("is_speaker") and not _.get("is_moderator") and not _.get("user_id") == self.client_id
        ]
        
        first_speaker = first_speaker[0] if first_speaker else self.host_info
        
        host_time = datetime.strptime(self.host_info.get("time_joined_as_speaker"), "%Y-%m-%dT%H:%M:%S.%f%z")
        first_speaker_time = datetime.strptime(first_speaker.get("time_joined_as_speaker"), "%Y-%m-%dT%H:%M:%S.%f%z")
        
        earliest_recorded_time = min(host_time, first_speaker_time)
        
        self.time_created = earliest_recorded_time
        logging.info(f"Earliest Recorded Time: {self.time_created}")
    
    def set_token(self):
        self.token = self.join_info.get("token")  # For audio client
        logging.info(f"Token: {self.token}")
    
    def set_users_already_in_room(self):
        users = self.join_info.get("users")
        self.already_in_room_set = set(_.get("user_id") for _ in users)
    
    def set_chat_enabled(self, on_join=False, channel_info=None):
        
        if on_join:
            self.chat_enabled = self.join_info.get("is_chat_enabled")
            return self.chat_enabled
        
        if channel_info:
            self.chat_enabled = channel_info.get("is_chat_enabled")
            return self.chat_enabled
        
        self.chat_enabled = self.channel_info.get("is_chat_enabled")
        logging.info(f"Chat Enabled: {self.chat_enabled}")
    
    def refresh_channel_status(self):
        self.reset_client_status()
        
        if not self.channel_info or not self.channel_info.get("success"):
            self.channel_active = False
            return {}, {}, {}
        
        self.channel_active = True
        self.set_chat_enabled()
        
        return self.channel_info, self.users_info, self.client_info
    
    # ----------------- Client Status ----------------- #
    def set_speaker_status(self):
        self.active_speaker = self.client_info.get("is_speaker")
        
        if self.active_speaker:
            self.granted_speaker = True
            self.waiting_speaker = False
    
    def set_mod_status(self):
        self.active_mod = self.client_info.get("is_moderator")
        
        if self.active_mod:
            self.granted_mod = True
            self.waiting_mod = False
    
    def set_client_status(self):
        self.set_speaker_status()
        self.set_mod_status()
    
    def reset_client_status(self):
        self.get_channel_info()
        if not self.channel_info or not self.channel_info.get("success"):
            return
        
        self.get_users_info()
        self.get_client_info()
        self.set_client_status()
    
    @set_interval(30)
    def keep_alive_ping(self):
        self.channel.active_ping(self.channel_id)
        return True
    
    # ----------------- Client Actions----------------- #
    def attempt_active_speaker(self):
        if self.auto_speaker_approval:
            self.channel.become_speaker(self.channel_id)
        else:
            # self.channel.accept_speaker_invite(self.channel_id, self.client_id)
            self.channel.become_speaker(self.channel_id)
    
    def recheck_speaker_status(self, interval, active_speaker_status):
        self.granted_speaker = False
        self.waiting_speaker = True
        
        while not active_speaker_status.isSet():
            # Which of these do I need?
            # self.channel.accept_speaker_invite(self.channel_id, self.client_id)
            self.channel.become_speaker(self.channel_id)
            self.reset_client_status()
            
            if self.granted_speaker:
                active_speaker_status.set()
                logging.info(f"Stopped: {self.waiting_speaker_thread}")
            
            else:
                logging.info("Still waiting to join stage")
            
            active_speaker_status.wait(interval)
    
    def wait_to_speak(self, interval=5, timeout=600):
        self.channel.audience_reply(self.channel_id)
        
        active_speaker_status = threading.Event()
        self.waiting_speaker_thread = threading.Thread(
            target=self.recheck_speaker_status, args=(interval, active_speaker_status))
        
        self.waiting_speaker_thread.daemon = True
        self.waiting_speaker_thread.start()
        logging.info(f"Started: {self.waiting_speaker_thread}")
        self.waiting_speaker_thread.join(timeout)
        logging.info(f"Joined: {self.waiting_speaker_thread}")
        active_speaker_status.set()
        
        return True if self.active_speaker else False
    
    def recheck_mod_status(self, interval, active_mod_status):
        
        while not active_mod_status.isSet():
            self.reset_client_status()
            
            if self.granted_mod:
                active_mod_status.set()
                logging.info(f"Stopped: {self.waiting_mod_thread}")
            
            else:
                logging.info("Still waiting mod privileges")
            
            active_mod_status.wait(interval)
    
    def wait_for_mod(self, interval=5, timeout=300):
        
        active_mod_status = threading.Event()
        self.waiting_mod_thread = threading.Thread(
            target=self.recheck_mod_status, args=(interval, active_mod_status))
        
        self.waiting_mod_thread.daemon = True
        self.waiting_mod_thread.start()
        logging.info(f"Started: {self.waiting_mod_thread}")
        self.waiting_mod_thread.join(timeout)
        logging.info(f"Joined: {self.waiting_mod_thread}")
        active_mod_status.set()
        
        return True if self.active_mod else False
    
    def send_room_chat(self, message, delay=10):
        if not self.chat_enabled:
            return
        
        response = {"success": False, "error_message": "internal response - send_room_chat"}
        message = [message] if isinstance(message, str) else message if isinstance(message, list) else None
        
        if not message:
            return response
        
        for _ in message:
            response = self.chat.send_chat(self.channel_id, _)
            sleep(delay)
        
        return response
    
    def send_hello_message(self, delay=5):
        response = False
        
        if self.host_id == 2350087:
            self.host_name = "Disco Doggie"

        message_list = [
            f"Yeeeer @{self.host_name}",
            f"Yeeeer...AutoMod in the spot! Hey {self.host_name}!",
            f"Hey {self.host_name}. What y'all on?",
            f"Hey {self.host_name}....throw me a green",
            f"Hey {self.host_name}....throw me a bean",
            f"What's good @{self.host_name}?",
            f"What you on @{self.host_name}?",
            f"What's happening @{self.host_name}?",
            f"What's good @{self.host_name}?",
            f"What the bidness is @{self.host_name}?",
            f"What's good y'all? Hey @{self.host_name}.",
        ]

        message = self.welcome_msg.get(str(self.host_name)) or random.choice(message_list)
        send = self.send_room_chat(message, delay)
        logging.info(f"Hello Message: {send}, {message}")
        
        if not send:
            return False
        
        if send.get("success") is not False:
            return send.get("success")
        
        if send.get("error_message") and "something like that" in send.get("error_message"):
            message = random.choice(message_list)
            response = self.send_room_chat(message, delay)
            logging.info(f"Sent alternate hello message: {message}")
            logging.info(response)
            return response

        logging.info(response)
        return response
    
    def set_announcement(self, message, interval, delay=None):
        
        @self.set_interval(interval * 60)
        def announcement():
            if not self.chat_enabled:
                return True
            
            response = self.send_room_chat(message, delay)
            response = response.get("success")
            return response
        
        return announcement()
    
    def wait_for_reconnection(self, interval=20, timeout=120):
        
        active_channel_status = threading.Event()
        self.waiting_reconnect_thread = threading.Thread(
            target=self.recheck_connection_status, args=(interval, active_channel_status))
        
        self.waiting_reconnect_thread.daemon = True
        self.waiting_reconnect_thread.start()
        logging.info(f"Started: {self.waiting_reconnect_thread}")
        self.waiting_reconnect_thread.join(timeout)
        logging.info(f"Joined: {self.waiting_reconnect_thread}")
        
        return True if self.channel_active else False
    
    def recheck_connection_status(self, interval, active_channel_status):
        
        while not active_channel_status.isSet():
            join = self.channel.join_channel(self.channel_id)
            if join and join.get("success"):
                self.channel_active = True
            
            elif join and join.get("success") is False:
                logging.info(join)
                
                if join.get("error_message") and "That room is no longer available" in join.get("error_message"):
                    active_channel_status.set()
                    logging.info("Channel is closed")
                    logging.info(f"Stopped: {self.waiting_reconnect_thread}")
                    
                elif join.get("error_message") and "The live room has ended" in join.get("error_message"):
                    active_channel_status.set()
                    logging.info("Channel is closed")
                    logging.info(f"Stopped: {self.waiting_reconnect_thread}")
            
            if self.channel_active:
                active_channel_status.set()
                logging.info(f"Stopped: {self.waiting_reconnect_thread}")
            else:
                logging.info("Still attempting to reconnect")
            
            active_channel_status.wait(interval)
    
    def set_welcome_message(self, first_name, user_id):
        
        if user_id == 2350087:
            first_name = "Disco Doggie"
            
        message_list = [
            f"Yeeeer @{first_name}",
            f"Hey @{first_name}. What you on?",
            f"What's good @{first_name}?",
            f"@{first_name} what's good?",
            f"What you on @{first_name}?",
            f"@{first_name} what you on?",
            f"What's happening @{first_name}?",
            f"What's good @{first_name}?",
            f"What the bidness is @{first_name}?",
            f"Nice to see you @{first_name}! 🎉",
            f"Heeeeey @{first_name}! 🥳",
            f"¡Hola {first_name}! 🎊",
            f"@{first_name} what's the word?",
            f"What's the word? @{first_name}",
        ]
        
        message = self.welcome_msg.get(str(user_id)) or random.choice(message_list)
            
        if user_id in [1232478029, 492945]:
            message = " ".join([message, " 👑🐺💙"])

        return message
    
    def welcome_guests(self, message_delay=5):
        
        cleared = self.mod_list.union(self.vip_list)
        
        if self.channel_type == "private" or self.channel_type == "social" or self.channel_type == "lounge":
            welcome_list = [_ for _ in self.users_info]
        else:
            welcome_list = [_ for _ in self.users_info if _.get("user_id") in cleared]
            
        for user in welcome_list:
            if user.get("user_id") in self.already_welcomed_set:
                continue
            
            print(f"welcome_guests, not welcomed {user.get('user_id')}")
            welcome_message = self.set_welcome_message(user.get("first_name"), user.get("user_id"))
            logging.info(welcome_message)
                
            welcome = self.send_room_chat(welcome_message, message_delay)
            
            if welcome and (welcome.get("success") is False):
                error_message = welcome.get("error_message")
                logging.info(error_message)
                if "Less is more" in error_message:
                    sleep(15)
                
                break
                
            self.already_welcomed_set.add(user.get("user_id"))
            
            sleep(message_delay)
    
    def invite_guests(self, message_delay=2):
    
        welcome = self.mod_list.union(self.vip_list)
        invite = welcome.union(self.guest_list)
        invite_list = [_ for _ in self.users_info if _.get("user_id") in invite]
    
        remove = [_ for _ in self.users_info if _.get("user_id") in self.remove_list]
        
        for user in invite_list:
            invited_user = False
        
            if not user.get("is_speaker") and not user.get("is_invited_as_speaker"):
                self.mod.invite_speaker(self.channel_id, user.get("user_id"))
                logging.info(f"Attempted to invite {user.get('user_id')} to speak")
                invited_user = True
                
            if self.chat_enabled and user.get("user_id") not in self.already_welcomed_set:

                if invited_user or user.get("user_id") in welcome:

                    welcome_message = self.set_welcome_message(user.get("first_name"), user.get("user_id"))
                    send = self.send_room_chat(welcome_message, message_delay)

                    if send and send.get("success"):
                        self.already_welcomed_set.add(user.get("user_id"))
                        sleep(message_delay)

                    continue
                
            self.already_welcomed_set.add(user.get("user_id"))
            
        if not remove:
            return True
        
        for user in remove:
            self.mod.remove_user(self.channel_id, user.get("user_id"))
        
        return True
    
    def mod_guests(self):
        
        mod_list = [_ for _ in self.users_info if _.get("user_id") in self.mod_list and _.get("is_moderator") is False]
        
        for user in mod_list:
            if user.get("is_speaker"):
                self.mod.make_moderator(self.channel_id, user.get("user_id"))
                logging.info(f"Attempted to make {user.get('first_name')} a moderator")

    def get_all_shares(self):
    
        share_list = []
        next_cursor = True
    
        count = 0
        while next_cursor and next_cursor not in self.share_cursors and next_cursor not in self.share_ids:
            
            if next_cursor == True:
                next_cursor = None
                
            shares = self.mod.get_channel_shares(self.channel_id, next_cursor)
            share_list.append(shares)
            self.share_cursors.add(next_cursor)
                
            items = shares and shares.get("shares")
            if not items:
                break
                    
            share_ids = [_.get("share_id") for _ in items]
            if not share_ids:
                break
                
            share_ids = share_ids[:-1]
            for val in share_ids:
                self.share_ids.add(val)
            
            next_cursor = shares.get("next_cursor")
            if count == 10:
                sleep(5)
            
        if not share_list:
            return
            
        for cursor in share_list:
            shares = cursor.get("shares")
            
            if shares:
                user_ids = [_.get("user_profile").get("user_id") for _ in shares]
                self.has_shared_room = self.has_shared_room.union(set(user_ids))
            
    def shoot_the_stage(self):
        target_list = [_ for _ in self.users_info if _.get("is_speaker") and _.get("user_id") not in self.has_shared_room]
        for user in target_list:
            if not user.get("is_moderator"):
                self.mod.uninvite_speaker(self.channel_id, user.get("user_id"))
                logging.info(f"Attempted to uninvite {user.get('first_name')}")
    
    # ----------------- Terminate Channel----------------- #

    def terminate_channel_mod(self):
        self.channel.leave_channel(self.channel_id)
        
        if self.keep_alive_thread:
            self.keep_alive_thread.set()
        
        if self.announcement_thread:
            self.announcement_thread.set()
        
        self.channel_id = 0
        self.join_info = {}
        self.channel_info = {}
        self.users_info = {}
        self.client_info = {}
        
        self.targeted_message = ""
        self.hello_message = ""
        self.hello_message_alt = ""
        
        self.channel_url = ""
        self.host_info = {}
        self.host_name = ""
        self.host_id = 0
        self.creator_id = 0
        self.channel_type = ""
        self.club_id = 0
        self.chat_enabled = False
        self.auto_speaker_approval = False
        self.time_created = ""
        self.token = ""

        self.has_shared_room = set()
        self.has_shared_room.add(self.client_id)
        self.share_cursors = set()
        self.share_ids = set()
        
        self.channel_active = False
        self.waiting_speaker = False
        self.granted_speaker = False
        self.active_speaker = False
        self.waiting_mod = False
        self.granted_mod = False
        self.active_mod = False
        
        self.screened_user_set = set()
        self.unscreened_user_set = set()
        self.screened_for_speaker_set = set()
        self.screened_for_mod_set = set()
        self.already_welcomed_set = set()
        self.filtered_users_list = []
        
        self.url_announcement = False
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    



    
    
    
            
            
            
            
            
            
            
            
            
            
    
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    
