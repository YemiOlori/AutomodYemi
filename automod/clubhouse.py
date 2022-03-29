#!/usr/bin/python -u
#-*- coding: utf-8 -*-
# pylint: disable=line-too-long,too-many-arguments,too-many-lines
# pylint: disable=no-self-argument,not-callable

"""
clubhouse.py
"""

import uuid
import random
import secrets
import functools
import requests
import logging
from configparser import ConfigParser


def load_config(config_file=""):
    """A function to read the config file."""
    config_object = ConfigParser()
    config_object.read(config_file)
    return config_object


def section_key_exception(config_object, section):
    if section not in config_object.sections():
        raise Exception(f"Error in fetching config in read_config method. {section} not found in config file.")


def config_to_dict(config_object, section, item=None):
    section_key_exception(config_object, section)
    config_section = dict(config_object[section])
    if not item:
        return config_section
    config_item = config_section[item]
    # Return None if section does not exist
    return config_item


def config_to_list(config_object, section):
    section_key_exception(config_object, section)
    config_section = config_object[section]
    item_list = []
    for item in config_section:
        item_list.append(config_section[item])
    config_section = item_list
    # Return None if section does not exist
    return config_section


def reload_client():
    """
    A function to reload Clubhouse client from previous session.

    :param client: A Clubhouse object
    :return client: A Clubhouse object updated with configuration information
    """
    config_file = "/Users/deon/Documents/GitHub/HQ/setting.ini"
    config_object = load_config(config_file)
    user_config = config_to_dict(config_object, "Account")
    client_id = user_config.get("client_id")
    user_token = user_config.get("user_token")
    user_device = user_config.get("user_device")
    refresh_token = user_config.get("refresh_token")
    access_token = user_config.get("access_token")
    if not client_id or not user_token or not user_device:
        logging.info("Reload client not successful")
        return {}
    reload_dict = {
        "client_id": client_id,
        "user_token": user_token,
        "user_device": user_device,
    }
    logging.info("Reload client successful")
    return reload_dict


# Remove this decorator as endpoints are testes
def unstable_endpoint(func):
    """ Simple decorator to warn that this endpoint is never tested at all. """
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        print("[!] This endpoint is NEVER TESTED and MAY BE UNSTABLE. BE CAREFUL!")
        return func(self, *args, **kwargs)
    return wrap


class Helper:
    """
    Clubhouse Class

    Decorators:
        @require_authentication:
            - this means that the endpoint requires authentication to access.

        @unstable_endpoint
            - This means that the endpoint is never tested.
            - Likely to be endpoints that were taken from a static analysis
    """
    reload_dict = reload_client()

    @staticmethod
    def require_authentication(func):
        """ Simple decorator to check for the authentication """
        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            if not (self.HEADERS.get("CH-UserID") and
                    self.HEADERS.get("CH-DeviceId") and
                    self.HEADERS.get("Authorization")):
                raise Exception('Not Authenticated')
            return func(self, *args, **kwargs)
        return wrap

    # App/API Information
    # Last Updated 3.12.2022
    API_URL = "https://www.clubhouseapi.com/api"
    API_BUILD_ID = "1104"
    API_BUILD_VERSION = "1.0.43"
    API_UA = f"clubhouse/{API_BUILD_ID} (iPhone; iOS 15.2; Scale/3.00)"
    API_UA_STATIC = f"Clubhouse/{API_BUILD_ID} CFNetwork/1327.0.4 Darwin/21.2.0"

    # Some useful information for communication
    # Where do these keys come from?
    PUBNUB_PUB_KEY = "pub-c-6878d382-5ae6-4494-9099-f930f938868b"
    PUBNUB_SUB_KEY = "sub-c-a4abea84-9ca3-11ea-8e71-f2b83ac9263d"
    PUBNUB_API_URL = "https://clubhouse.pubnubapi.com/v2"

    TWITTER_ID = "NyJhARWVYU1X3qJZtC2154xSI"
    TWITTER_SECRET = "ylFImLBFaOE362uwr4jut8S8gXGWh93S1TUKbkfh7jDIPse02o"

    INSTAGRAM_ID = "1352866981588597"
    INSTAGRAM_CALLBACK = "https://www.joinclubhouse.com/callback/instagram"

    AGORA_KEY = "938de3e8055e42b281bb8c6f69c21f78"
    SENTRY_KEY = "5374a416cd2d4009a781b49d1bd9ef44@o325556.ingest.sentry.io/5245095"
    INSTABUG_KEY = "4e53155da9b00728caa5249f2e35d6b3"
    AMPLITUDE_KEY = "9098a21a950e7cb0933fb5b30affe5be"

    # Useful header information
    HEADERS = {
        "CH-Languages": "en-US",
        "CH-Locale": "en_US",
        "Accept": "application/json",
        "Accept-Language": "en-US;q=1",
        "Accept-Encoding": "gzip, deflate",
        "CH-AppBuild": f"{API_BUILD_ID}",
        "CH-AppVersion": f"{API_BUILD_VERSION}",
        "User-Agent": f"{API_UA}",
        "Connection": "close",
        "Content-Type": "application/json; charset=utf-8",
        "Cookie": f"__cfduid={secrets.token_hex(21)}{random.randint(1, 9)}",
        'CH-UserID': reload_dict.get("client_id"),
        'Authorization': f"Token {reload_dict.get('user_token')}",
        'CH-DeviceId': reload_dict.get("user_device"),
        # "CH-DeviceId": str(uuid.uuid4()).upper(),
        # "Ch-Session-Id": str(uuid.uuid4()).upper(),
    }

    def __init__(self, client_id='', user_token='', user_device='', headers=None):
        """ (Clubhouse, str, str, str, dict) -> NoneType
        Set authenticated information
        """


        self.client_id = client_id if client_id else "(null)"
        # self.auth = Auth()
        # self.client = Client()
        # self.user = User()
        # self.notifications = Notifications()
        # self.channel = Channel()
        # self.mod = Mod()
        # self.chat = Chat()
        # self.message = Message()
        # self.event = Event()
        # self.club = Club()
        # self.topic = Topic()

    def __str__(self):
        """ (Clubhouse) -> str
        Get information about the given class.
        >>> clubhouse = Helper()
        >>> str(clubhouse)
        Clubhouse(user_id=(null), user_token=None, user_device=31525f52-6b67-40de-83c0-8f9fe0f6f409)
        """
        return "Clubhouse(user_Id={}, user_token={}, user_device={})".format(
            self.HEADERS.get('CH-UserID'),
            self.HEADERS.get('Authorization'),
            self.HEADERS.get('CH-DeviceId')
        )


class Clubhouse(Helper):
    def __init__(self):
        """ (Clubhouse, str, str, str, dict) -> NoneType
        Set authenticated information
        """
        super().__init__()
        self.auth = Auth()
        self.client = Client()
        self.user = User()
        self.notifications = Notifications()
        self.channel = Channel()
        self.mod = ChannelMod()
        self.chat = ChannelChat()
        self.message = Message()
        self.event = Event()
        self.club = Club()
        self.topic = Topic()


class Auth(Helper):
    def __init__(self):
        super().__init__()

    # Why doesn't this endpoint trigger a verification code?
    def start(self, phone_number):
        """ (Clubhouse, str) -> dict

        Begin phone number authentication.
        Some examples for the phone number.

        >>> clubhouse = Helper()
        >>> clubhouse.start_phone_number_auth("+821012341337")
        ...
        >>> clubhouse.start_phone_number_auth("+818013371221")
        ...
        """
        if self.HEADERS.get("Authorization"):
            raise Exception('Already Authenticated')
        data = {
            "tokens": {
                "rc_token": None,
                "device_token": None
            },
            "phone_number": phone_number
        }
        req = requests.post(f"{self.API_URL}/start_phone_number_auth", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    @unstable_endpoint
    def resend(self, phone_number):
        """ (Clubhouse, str) -> dict

        Resend the verification message
        """
        if self.HEADERS.get("Authorization"):
            raise Exception('Already Authenticated')
        data = {
            "tokens": {
                "rc_token": None,
                "device_token": None
            },
            "phone_number": phone_number
        }
        req = requests.post(f"{self.API_URL}/resend_phone_number_auth", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def complete(self, phone_number, rc_token, verification_code):
        """ (Clubhouse, str, str, str) -> dict

        Complete phone number authentication.
        NOTE: As of June 2021, ReCAPTCHA v3 has been introduced so you need to get that token ready...
        This should return `auth_token`, `access_token`, `refresh_token`, is_waitlisted, ...
        Please note that output may be different depending on the status of the authenticated user
        """
        if self.HEADERS.get("Authorization"):
            raise Exception('Already Authenticated')
        data = {
            "device_token": None,
            "rc_token": rc_token,
            "phone_number": phone_number,
            "verification_code": verification_code
        }
        req = requests.post(f"{self.API_URL}/complete_phone_number_auth", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def logout(self):
        """ (Clubhouse) -> dict

        Logout from the app.
        """
        data = {}
        req = requests.post(f"{self.API_URL}/logout", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class Client(Helper):
    def __init__(self):
        super().__init__()

    def me(self, return_blocked_ids=False, timezone_identifier="Asia/Tokyo", return_following_ids=False):
        """ (Clubhouse, bool, str, bool) -> dict

        Get my information
        """
        data = {
            "return_blocked_ids": return_blocked_ids,
            "timezone_identifier": timezone_identifier,
            "return_following_ids": return_following_ids
        }
        req = requests.post(f"{self.API_URL}/me", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def feed(self):
        """ (Clubhouse) -> dict

        Get list of channels, current invite status, etc.
        """
        req = requests.get(f"{self.API_URL}/get_feed?", headers=self.HEADERS)
        logging.info(req.json)
        return req.json()

    def profile(self, client_id='', username=''):
        """ (Clubhouse, str, str) -> dict

        Lookup someone else's profile. It is OK to one's own profile with this method.
        """
        data = {
            "query_id": None,
            "query_result_position": 0,
            "user_id": int(client_id) if client_id else None,
            "username": username if username else None
        }
        req = requests.post(f"{self.API_URL}/get_profile", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def ping_user(self, channel, user_id):
        """ (Clubhouse, str, int) -> dict

        Invite someone to a currently joined channel.
        It will send a ping notification to the given user_id.
        """
        data = {
            "channel": channel,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/invite_to_existing_channel", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def following(self, client_id, page_size=50, page=1):
        """ (Clubhouse, str, int, int) -> dict

        Get following users type2
        """
        query = "user_id={}&page_size={}&page={}".format(
            client_id,
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_following?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def followers(self, client_id, page_size=50, page=1):
        """ (Clubhouse, str, int, int) -> dict

        Get followers of the given user_id.
        """
        query = "user_id={}&page_size={}&page={}".format(
            client_id,
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_followers?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    # Added by Deon
    def search(self, query, followers_only=False, following_only=False, cofollows_only=False):
        """ (Clubhouse, str, bool, bool, bool) -> dict

                Search clubs based on the given query.
                """
        data = {
            "limit_to_object_types": [],
            "cofollows_only": cofollows_only,
            "following_only": following_only,
            "followers_only": followers_only,
            "query": query
        }
        req = requests.post(f"{self.API_URL}/search", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def get_clubs(self, is_startable_only=False):
        """ (Clubhouse, bool) -> dict

        Get list of clubs the user's in.
        """
        data = {
            "is_startable_only": is_startable_only
        }
        req = requests.post(f"{self.API_URL}/get_clubs", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def get_online_friends(self):
        """ (Clubhouse) -> dict

        List all online friends.
        """
        req = requests.post(f"{self.API_URL}/get_online_friends", headers=self.HEADERS, json={})
        logging.info(req)
        return req.json()

    def get_settings(self):
        """ (Clubhouse) -> dict

        Receive user's settings.
        """
        req = requests.get(f"{self.API_URL}/get_settings", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def add_email(self, email):
        """ (Clubhouse, str) -> dict

        Request for email verification.
        You only need to do this once.
        """
        data = {
            "email": email
        }
        req = requests.post(f"{self.API_URL}/add_email", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def add_topic(self, club_id=None, topic_id=None):
        """ (Clubhouse, int, int) -> dict

        Add user's interest.

        Some interesting flags for Language has been shared in the following link.
        Reference: https://github.com/grishka/Houseclub/issues/24
        """
        data = {
            "club_id": int(club_id) if club_id else None,
            "topic_id": int(topic_id) if topic_id else None
        }
        req = requests.post(f"{self.API_URL}/add_user_topic", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def remove_topic(self, club_id, topic_id):
        """ (Clubhouse, int, int) -> dict

        Remove user's interest
        """
        data = {
            "club_id": int(club_id) if club_id else None,
            "topic_id": int(topic_id) if topic_id else None
        }
        req = requests.post(f"{self.API_URL}/remove_user_topic", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_photo(self, photo_filename):
        """ (Clubhouse, str) -> dict

        Update photo. Please make sure to upload a JPG format.
        """
        files = {
            "file": ("image.jpg", open(photo_filename, "rb"), "image/jpeg"),
        }
        tmp = self.HEADERS['Content-Type']
        self.HEADERS.pop("Content-Type")
        req = requests.post(f"{self.API_URL}/update_photo", headers=self.HEADERS, files=files)
        self.HEADERS['Content-Type'] = tmp
        logging.info(req)
        return req.json()

    def update_bio(self, bio):
        """ (Clubhouse, str) -> dict

        Update bio on your profile
        """
        data = {
            "bio": bio
        }
        req = requests.post(f"{self.API_URL}/update_bio", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_name(self, name):
        """ (Clubhouse, str) -> dict

        Change your legal name. Be careful of what you're trying to enter.
            (1) Upon registration
            (2) Changing your legal name. YOU CAN ONLY DO THIS ONCE.
        """
        data = {
            "name": name,
        }
        req = requests.post(f"{self.API_URL}/update_name", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_username(self, username):
        """ (Clubhouse, str) -> dict

        Change username. YOU HAVE LIMITED NUMBER OF TRIALS TO CHANGE YOUR USERNAME.
        """
        data = {
            "username": username,
        }
        req = requests.post(f"{self.API_URL}/update_username", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    # This is same as username and needs to be fixed
    def update_displayname(self, name):
        """ (Clubhouse, str) -> dict

        Change your nickname. YOU CAN ONLY DO THIS ONCE.
        """
        data = {
            "name": name,
        }
        req = requests.post(f"{self.API_URL}/update_name", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_twitter_username(self, username, twitter_token, twitter_secret):
        """ (Clubhouse, str, str, str) -> dict

        Change Twitter username based on Twitter Token.

        >>> client.update_twitter_username(None, None, None) # Clear username
        >>> client.update_twitter_username("stereotype32", "...", "...") # Set username
        """
        data = {
            "username": username,
            "twitter_token": twitter_token,
            "twitter_secret": twitter_secret
        }
        req = requests.post(f"{self.API_URL}/update_twitter_username", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_instagram_username(self, code):
        """ (Clubhouse, str) -> dict

        Change Twitter username based on Instagram token.

        >>> client.update_instagram_username(None) # Clear username
        >>> client.update_instagram_username("...") # Set username
        """
        data = {
            "code": code
        }
        req = requests.post(f"{self.API_URL}/update_instagram_username", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_skintone(self, skintone=1):
        """ (Clubhouse, int) -> dict
        Updating skinetone for raising hands, etc.
        """
        skintone = int(skintone)
        if not 1 <= skintone <= 5:
            return False

        data = {
            "skintone": skintone
        }
        req = requests.post(f"{self.API_URL}/update_skintone", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_follow_notifications(self, client_id, notification_type=2):
        """ (Clubhouse, str, int) -> dict

        Update notification frequency for the given user.
        1 = Always notify, 2 = Sometimes, 3 = Never
        """
        data = {
            "user_id": int(client_id),
            "notification_type": int(notification_type)
        }
        req = requests.post(f"{self.API_URL}/update_follow_notifications", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def refresh_token(self, refresh_token):
        """ (Clubhouse, str) -> dict

        Refresh the JWT token. returns both access and refresh token.
        """
        data = {
            "refresh": refresh_token
        }
        req = requests.post(f"{self.API_URL}/refresh_token", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    @unstable_endpoint
    def report_incident(self, client_id, channel, incident_type, incident_description, email):
        """ (Clubhouse, int, str, unknown, str, str) -> dict

        Report incident
        There seemed to be a field for attachment, need to trace this later
        """
        data = {
            "user_id": int(client_id),
            "channel": channel,
            "incident_type": incident_type,
            "incident_description": incident_description,
            "email": email
        }
        req = requests.post(f"{self.API_URL}/report_incident", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class User(Helper):
    def __init__(self):
        super().__init__()

    def get_profile(self, user_id='', username=''):
        """ (Clubhouse, str, str) -> dict

        Lookup someone else's profile. It is OK to one's own profile with this method.
        """
        data = {
            "query_id": None,
            "query_result_position": 0,
            "user_id": int(user_id) if user_id else None,
            "username": username if username else None
        }
        req = requests.post(f"{self.API_URL}/get_profile", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def follow(self, user_id, user_ids=None, source=4, source_topic_id=None):
        """ (Clubhouse, int, list, int, int) -> dict

        Follow a user.
        Different value for `source` may require different parameters to be set
        """
        data = {
            "source_topic_id": source_topic_id,
            "user_ids": user_ids,
            "user_id": int(user_id),
            "source": source
        }
        req = requests.post(f"{self.API_URL}/follow", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def unfollow(self, user_id):
        """ (Clubhouse, int) -> dict

        Unfollow a user.
        """
        data = {
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/unfollow", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def follow_multiple(self, user_ids, user_id=None, source=7, source_topic_id=None):
        """ (Clubhouse, list, int, int, int) -> dict

        Follow multiple users at once.
        Different value for `source` may require different parameters to be set
        """
        data = {
            "source_topic_id": source_topic_id,
            "user_ids": user_ids,
            "user_id": user_id,
            "source": source
        }
        req = requests.post(f"{self.API_URL}/follow_multiple", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def following(self, user_id, page_size=50, page=1):
        """ (Clubhouse, str, int, int) -> dict

        Get following users type2
        """
        query = "user_id={}&page_size={}&page={}".format(
            user_id,
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_following?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def followers(self, user_id, page_size=50, page=1):
        """ (Clubhouse, str, int, int) -> dict

        Get followers of the given user_id.
        """
        query = "user_id={}&page_size={}&page={}".format(
            user_id,
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_followers?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def mutual_follows(self, user_id, page_size=50, page=1):
        """ (Clubhouse, str, int, int) -> dict

        Get mutual followers between the current user and the given user_id.
        """
        query = "user_id={}&page_size={}&page={}".format(
            user_id,
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_mutual_follows?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def block(self, user_id):
        """ (Clubhouse, int) -> dict

        Block a user.
        """
        data = {
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/block", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def unblock(self, user_id):
        """ (Clubhouse, int) -> dict

        Unfollow a user.
        """
        data = {
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/unblock", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    # What is this?
    def get_events_for_user(self, user_id='', page_size=25, page=1):
        """ (Clubhouse, str, int, int) -> dict

        Get events for the specific user.
        """
        query = f"user_id={user_id}&page_size={page_size}&page={page}"
        req = requests.get(f"{self.API_URL}/get_events_for_user?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()


class Notifications(Helper):
    def __init__(self):
        super().__init__()

    def get(self, page_size=20, page=1):
        """ (Clubhouse, int, int) -> dict

        Get my notifications.
        """
        query = f"page_size={page_size}&page={page}"
        req = requests.get(f"{self.API_URL}/get_notifications?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def get_actionable(self):
        """ (Clubhouse, int, int) -> dict

        Get notifications. This may return some notifications that require some actions
        """
        req = requests.get(f"{self.API_URL}/get_actionable_notifications", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    @unstable_endpoint
    def ignore_actionable(self, actionable_notification_id):
        """ (Clubhouse, int) -> dict

        Ignore the actionable notification.
        """
        data = {
            "actionable_notification_id": actionable_notification_id
        }
        req = requests.post(f"{self.API_URL}/ignore_actionable_notification", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class Channel(Helper):
    def __init__(self):
        super().__init__()

    def get(self, channel, channel_id=None):
        """ (Clubhouse, str, int) -> dict

        Get information of the given channel
        """
        data = {
            "channel": channel,
            "channel_id": channel_id
        }
        req = requests.post(f"{self.API_URL}/get_channel", headers=self.HEADERS, json=data)
        req_json = req.json()
        logging.info(req_json)
        if req_json.get("should_leave"):
            raise Exception

        return req_json

    def join(self, channel, attribution_source="feed",
             attribution_details="eyJpc19leHBsb3JlIjpmYWxzZSwicmFuayI6MX0="):
        """ (Clubhouse, str, str) -> dict

        Join the given channel
        """
        data = {
            "channel": channel,
            "attribution_source": attribution_source,
            "attribution_details": attribution_details,  # base64_json
            # logging_context (json of some details)
        }
        req = requests.post(f"{self.API_URL}/join_channel", headers=self.HEADERS, json=data)
        logging.info(data)
        logging.info(req.json())
        return req.json()

    def audience_reply(self, channel, raise_hands=True, unraise_hands=False):
        """ (Clubhouse, str, bool, bool) -> bool

        Request for raise_hands.
        """
        data = {
            "channel": channel,
            "raise_hands": raise_hands,
            "unraise_hands": unraise_hands
        }
        req = requests.post(f"{self.API_URL}/audience_reply", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def accept_speaker_invite(self, channel, client_id):
        """ (Clubhouse, str, int) -> dict

        Accept speaker's invitation, based on the (channel, invited_moderator)
        `raise_hands` needs to be called first, prior to the invitation.
        """
        data = {
            "channel": channel,
            "user_id": int(client_id)
        }
        req = requests.post(f"{self.API_URL}/accept_speaker_invite", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def reject_speaker_invite(self, channel, client_id):
        """ (Clubhouse, str, int) -> dict

        Reject speaker's invitation.
        """
        data = {
            "channel": channel,
            "user_id": int(client_id)
        }
        req = requests.post(f"{self.API_URL}/reject_speaker_invite", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_audio_mode(self, channel):
        """ (Clubhouse, str) -> dict
        audio_profile for music mode is 11
        Get events for the specific user.
        """
        # audio_profile 11 updates to music mode
        data = {
            "channel": channel,
            "audio_profile": 11,
            "is_on_call": False
        }
        req = requests.post(f"{self.API_URL}/update_channel_user_status", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def active_ping(self, channel):
        """ (Clubhouse, str) -> dict

        Keeping the user active while being in a chatroom
        """
        data = {
            "channel": channel,
            "chanel_id": None
        }
        req = requests.post(f"{self.API_URL}/active_ping", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def leave(self, channel):
        """ (Clubhouse, str) -> dict

        Leave the given channel
        """
        data = {
            "channel": channel
        }
        req = requests.post(f"{self.API_URL}/leave_channel", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def create(self, topic="", user_ids=(), is_private=False, is_social_mode=False):
        """ (Clubhouse, str, list, bool, bool) -> dict

        Create a new channel. Type of the room can be changed
        """
        data = {
            "is_social_mode": is_social_mode,
            "is_private": is_private,
            "club_id": None,
            "user_ids": user_ids,
            "event_id": None,
            "topic": topic
        }
        req = requests.post(f"{self.API_URL}/create_channel", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    # Is this a private room or a wave?
    @unstable_endpoint
    def invite_to_new_channel(self, user_id, channel):
        """ (Clubhouse, int, str) -> dict

        Invite someone to the channel
        """
        data = {
            "user_id": int(user_id),
            "channel": channel
        }
        req = requests.post(f"{self.API_URL}/invite_to_new_channel", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    # Is this a private room or a wave?
    @unstable_endpoint
    def accept_new_channel_invite(self, channel_invite_id):
        """ (Clubhouse, int) -> dict

        Accept Channel Invitation
        """
        data = {
            "channel_invite_id": channel_invite_id
        }
        req = requests.post(f"{self.API_URL}/accept_new_channel_invite", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    @unstable_endpoint
    def reject_new_channel_invite(self, channel_invite_id):
        """ (Clubhouse, int) -> dict

        Reject Channel Invitation
        """
        data = {
            "channel_invite_id": channel_invite_id
        }
        req = requests.post(f"{self.API_URL}/reject_new_channel_invite", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    @unstable_endpoint
    def cancel_new_channel_invite(self, channel_invite_id):
        """ (Clubhouse, int) -> dict

        Cancel Channel Invitation
        """
        data = {
            "channel_invite_id": channel_invite_id
        }
        req = requests.post(f"{self.API_URL}/cancel_new_channel_invite", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def hide(self, channel, hide=True):
        """ (Clubhouse, str, bool) -> dict

        Hide/unhide the channel from the channel list.
        """
        # Join channel
        data = {
            "channel": channel,
            "hide": hide
        }
        req = requests.post(f"{self.API_URL}/hide_channel", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    # What is this?
    def get_create_channel_targets(self):
        """ (Clubhouse) -> dict

        Not sure what this does. Triggered upon channel creation
        """
        data = {}
        req = requests.post(f"{self.API_URL}/get_create_channel_targets", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class ChannelMod(Helper):
    def __init__(self):
        super().__init__()

    def make_moderator(self, channel, user_id):
        """ (Clubhouse, str, int) -> dict

        Make the given user moderator. Requires moderator privilege.
        """
        data = {
            "channel": channel,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/make_moderator", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def uninvite_speaker(self, channel, user_id):
        """ (Clubhouse, str, int) -> dict

        Move audience to speaker. Requires moderator privilege.
        """
        data = {
            "channel": channel,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/invite_speaker", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def move_speaker(self, channel, user_id):
        """ (Clubhouse, str, int) -> dict

        Move speaker to audience. Requires moderator privilege.
        """
        data = {
            "channel": channel,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/uninvite_speaker", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def mute_speaker(self, channel, user_id):
        """ (Clubhouse, str, int) -> dict

        Mute speaker. Requires moderator privilege
        """
        data = {
            "channel": channel,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/mute_speaker", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def add_link(self, channel, link):
        """ (Clubhouse, str, str) -> dict

        Pin a room link.
        """
        data = {
            "channel": channel,
            "link": link
        }
        req = requests.post(f"{self.API_URL}/add_channel_link", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def remove_link(self, channel):
        """ (Clubhouse, str, str) -> dict

        Remove pinned room link.
        """
        channel_info = get_channel(self, channel, channel_id=None)
        link_id = channel_info['links'][0]['link_id']

        data = {
            "channel": channel,
            "link": link_id
        }
        req = requests.post(f"{self.API_URL}/remove_channel_link", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def make_public(self, channel, channel_id=None):
        """ (Clubhouse, str, int) -> dict

        Make the current channel open to public.
        Everyone can join the channel.
        """
        data = {
            "channel": channel,
            "channel_id": channel_id
        }
        req = requests.post(f"{self.API_URL}/make_channel_public", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def make_social(self, channel, channel_id=None):
        """ (Clubhouse, str, int) -> dict

        Make the current channel open to public.
        Only people who user follows can join the channel.
        """
        data = {
            "channel": channel,
            "channel_id": channel_id
        }
        req = requests.post(f"{self.API_URL}/make_channel_social", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def end(self, channel, channel_id=None):
        """ (Clubhouse, str, int) -> dict

        Kick everyone and close the channel. Requires moderator privilege.
        """
        data = {
            "channel": channel,
            "channel_id": channel_id
        }
        req = requests.post(f"{self.API_URL}/end_channel", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def remove_user(self, channel, user_id):
        """ (Clubhouse, str, int) -> dict

        Remove the user from the channel. The user will not be able to re-join.
        """
        data = {
            "channel": channel,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/block_from_channel", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def change_handraising(self, channel, is_enabled=True, handraise_permission=1):
        """ (Clubhouse, bool, int) -> dict

        Change handraise settings. Requires moderator privilege

        * handraise_permission(int)
           - 1: Everyone
           - 2: Followed by the speakers
        * is_enabled(bool)
           - True: Enable handraise
           - False: Disable handraise
        """
        handraise_permission = int(handraise_permission)
        if not 1 <= handraise_permission <= 2:
            return False

        data = {
            "channel": channel,
            "is_enabled": is_enabled,
            "handraise_permission": handraise_permission
        }
        req = requests.post(f"{self.API_URL}/change_handraise_settings", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class ChannelChat(Helper):
    def __init__(self):
        super().__init__()

    def get(self, channel):
        """ (Clubhouse, str) -> dict

        Get events for the specific user.
        """
        query = f"channel={channel}&is_chronological_order=0"
        req = requests.get(f"{self.API_URL}/get_channel_messages?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def send_chat(self, channel, message):
        """ (Clubhouse, str, str) -> dict

        Get events for the specific user.
        """
        data = {
            "channel": channel,
            "message": message
        }
        req = requests.post(f"{self.API_URL}/send_channel_message", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class Message(Helper):
    def __init__(self):
        super().__init__()

    # Does this work?
    def get_feed(self):
        """ (Clubhouse, str, str) -> dict

        Get events for the specific user.
        """
        req = requests.get(f"{self.API_URL}/get_chats", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def create(self, participant_ids):
        """ (Clubhouse, list) -> dict

        Get events for the specific user.
        """
        data = {
            "source": 4,
            "participant_ids": participant_ids
        }
        req = requests.post(f"{self.API_URL}/create_chat", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def search(self, participant_ids):
        """ (Clubhouse, str, str) -> dict

        Get events for the specific user.
        """
        data = {
            "source": None,
            "participant_ids": participant_ids
        }
        req = requests.post(f"{self.API_URL}/search_chats", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def get_message(self, chat_id):
        """ (Clubhouse, str) -> dict

        Get events for the specific user.
        """
        req = requests.get(f"{self.API_URL}/get_chat_messages?chat_id={chat_id}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def get_message_thread(self, participant_ids):
        """ (Clubhouse, str, list) -> dict

        Get events for the specific user.
        """
        _search = self.search_chats(participant_ids)

        if _search["success"]:

            if len(_search["chats"]) > 0:
                chat_id = _search["chats"][0]["chat_id"]
                req = self.get_chat_messages(chat_id)

            else:
                return "[.] No chat history"
        logging.info(req)
        return req.json

    def get_message_id(self, participant_ids):
        chat_id = False
        _search = self.search_backchannel(participant_ids)
        if _search["success"]:
            if len(_search["chats"]) > 0:
                chat_id = _search["chats"][0]["chat_id"]
        else:
            req = self.create_backchannel(participant_ids)
            if req.get("success"):
                chat_id = req["chat_id"]
        logging.info(req)
        return chat_id

    # Check to see if this is correct
    def send(self, message, chat_id=None, participant_ids=None):
        """ (Clubhouse, str, list) -> dict

        Get events for the specific user.
        """
        if not chat_id:
            chat_id = self.get_chat_id(participant_ids)

        data = {
            "chat_id": chat_id,
            "client_message_id": str(uuid.uuid4()),
            "message_body": message
        }

        req = requests.post(f"{self.API_URL}/send_chat_message", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class Event(Helper):
    def __init__(self):
        super().__init__()

    def get(self, event_id=None, user_ids=None, club_id=None, is_member_only=False, event_hashid=None,
                  description=None, time_start_epoch=None, name=None):
        """ (Clubhouse, int, list, int, bool, int, str, int, str) -> dict

        Get details about the event
        """
        data = {
            # "user_ids": user_ids,
            # "club_id": club_id,
            # "is_member_only": is_member_only,
            "event_id": int(event_id) if event_id else None,
            # "event_hashid": event_hashid,
            # "description": description,
            # "time_start_epoch": time_start_epoch,
            # "name": name
        }
        req = requests.post(f"{self.API_URL}/get_event", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def create(self, name, time_start_epoch, description, event_id=None, user_ids=(), club_id=None,
               is_member_only=False, event_hashid=None):
        """ (Clubhouse, str, int, str, int, list, int, bool, int) -> dict

        Create a new event
        """
        data = {
            "user_ids": user_ids,
            "club_id": club_id,
            "is_member_only": is_member_only,
            "event_id": int(event_id) if event_id else None,
            "event_hashid": event_hashid,
            "description": description,
            "time_start_epoch": time_start_epoch,
            "name": name
        }
        req = requests.post(f"{self.API_URL}/edit_event", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def edit(self, name, time_start_epoch, description, event_id=None, user_ids=(), club_id=None,
             is_member_only=False, event_hashid=None):
        """ (Clubhouse, str, int, str, int, list, int, bool, int) -> dict

        Edit an event.
        """
        data = {
            "user_ids": user_ids,
            "club_id": club_id,
            "is_member_only": is_member_only,
            "event_id": int(event_id) if event_id else None,
            "event_hashid": event_hashid,
            "description": description,
            "time_start_epoch": time_start_epoch,
            "name": name
        }
        req = requests.post(f"{self.API_URL}/edit_event", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def delete(self, event_id, user_ids=None, club_id=None, is_member_only=False, event_hashid=None,
               description=None, time_start_epoch=None, name=None):
        """ (Clubhouse, str, list, int, bool, int, str, int, str) -> dict

        Delete event.
        """
        data = {
            "user_ids": user_ids,
            "club_id": club_id,
            "is_member_only": is_member_only,
            "event_id": int(event_id) if event_id else None,
            "event_hashid": event_hashid,
            "description": description,
            "time_start_epoch": time_start_epoch,
            "name": name
        }
        req = requests.post(f"{self.API_URL}/delete_event", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def get_events(self, is_filtered=True, page_size=25, page=1):
        """ (Clubhouse, bool, int, int) -> dict

        Get list of upcoming events with details.
        """
        _is_filtered = "true" if is_filtered else "false"
        query = "is_filtered={}&page_size={}&page={}".format(
            "true" if is_filtered else "false",
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_events?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    # What is this?
    def get_events_to_start(self):
        """ (Clubhouse) -> dict

        Get events to start
        """
        req = requests.get(f"{self.API_URL}/get_events_to_start", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def get_events_for_user(self, user_id='', page_size=25, page=1):
        """ (Clubhouse, str, int, int) -> dict

        Get events for the specific user.
        """
        query = f"user_id={user_id}&page_size={page_size}&page={page}"
        req = requests.get(f"{self.API_URL}/get_events_for_user?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()


class Club(Helper):
    def __init__(self):
        super().__init__()

    def get(self, club_id, source_topic_id=None):
        """ (Clubhouse, int, int) -> dict

        Get the information about the given club_id.
        """
        data = {
            "club_id": int(club_id),
            "source_topic_id": source_topic_id,
            "query_id": None,
            "query_result_position": None,
            "slug": None,
        }
        req = requests.post(f"{self.API_URL}/get_club", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def get_members(self, club_id, return_followers=False, return_members=True, page_size=50, page=1):
        """ (Clubhouse, int, bool, bool, int, int) -> dict

        Get list of members on the given club_id.
        """
        query = "club_id={}&return_followers={}&return_members={}&page_size={}&page={}".format(
            club_id,
            int(return_followers),
            int(return_members),
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_club_members?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def join(self, club_id, source_topic_id=None):
        """ (Clubhouse, int, int) -> dict

        Join a club
        """
        data = {
            "club_id": int(club_id),
            "source_topic_id": source_topic_id
        }
        req = requests.post(f"{self.API_URL}/join_club", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def leave(self, club_id, source_topic_id=None):
        """ (Clubhouse, int, int) -> dict

        Leave a club
        """
        data = {
            "club_id": int(club_id),
            "source_topic_id": source_topic_id
        }
        req = requests.post(f"{self.API_URL}/leave_club", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def add_club_admin(self, club_id, user_id):
        """ (Clubhouse, int, int) -> dict

        Add Club Admin. Requires privilege.
        """
        data = {
            "club_id": int(club_id),
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/add_club_admin", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def remove_club_admin(self, club_id, user_id):
        """ (Clubhouse, int, int) -> dict

        Remove Club admin. Requires privilege.
        """
        data = {
            "club_id": int(club_id) if club_id else None,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/remove_club_admin", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def remove_club_member(self, club_id, user_id):
        """ (Clubhouse, int, int) -> dict

        Remove Club member. Requires privilege.
        """
        data = {
            "club_id": int(club_id) if club_id else None,
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/remove_club_member", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def accept_club_member_invite(self, club_id, source_topic_id=None, invite_code=None):
        """ (Clubhouse, int, int, str) -> dict

        Accept Club member invite.
        """
        data = {
            "club_id": int(club_id) if club_id else None,
            "invite_code": invite_code,
            "query_id": None,
            "query_result_position": None,
            "slug": None,
            "source_topic_id": source_topic_id
        }
        req = requests.post(f"{self.API_URL}/accept_club_member_invite", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def add_club_member(self, club_id, user_id, name, phone_number, message, reason):
        """ (Clubhouse, int, int, str, str, str, unknown) -> dict

        Add club member
        """
        data = {
            "club_id": int(club_id),
            "user_id": int(user_id),
            "name": name,
            "phone_number": phone_number,
            "message": message,
            "reason": reason
        }
        req = requests.post(f"{self.API_URL}/add_club_member", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def get_club_nominations(self, club_id, source_topic_id):
        """ (Club, int, int) -> dict

        Get club nomination list
        """
        data = {
            "club_id": int(club_id),
            "source_topic_id": source_topic_id
        }
        req = requests.post(f"{self.API_URL}/get_club_nominations", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def approve_club_nomination(self, club_id, source_topic_id, invite_nomination_id):
        """ (Club, int, int) -> dict

        Approve club nomination
        """
        data = {
            "club_id": int(club_id),
            "source_topic_id": source_topic_id,
            "invite_nomination_id": invite_nomination_id
        }
        req = requests.post(f"{self.API_URL}/approve_club_nomination", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def reject_club_nomination(self, club_id, source_topic_id, invite_nomination_id):
        """ (Club, int, int) -> dict

        Reject club nomination
        """
        data = {
            "club_id": int(club_id),
            "source_topic_id": source_topic_id,
            "invite_nomination_id": invite_nomination_id
        }
        req = requests.post(f"{self.API_URL}/approve_club_nomination", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def add_club_topic(self, club_id, topic_id):
        """ (Club, int, int) -> dict

        Add club topic
        """
        data = {
            "club_id": int(club_id),
            "topic_id": int(topic_id)
        }
        req = requests.post(f"{self.API_URL}/add_club_topic", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def remove_club_topic(self, club_id, topic_id):
        """ (Club, int, int) -> dict

        Remove club topic
        """
        data = {
            "club_id": int(club_id),
            "topic_id": int(topic_id)
        }
        req = requests.post(f"{self.API_URL}/remove_club_topic", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_is_follow_allowed(self, club_id, is_follow_allowed=True):
        """ (Clubhouse, int, bool) -> dict

        Update follow button of the given Club
        """
        data = {
            "club_id": int(club_id),
            "is_follow_allowed": is_follow_allowed
        }
        req = requests.post(f"{self.API_URL}/update_is_follow_allowed", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_is_membership_private(self, club_id, is_membership_private=False):
        """ (Clubhouse, int, bool) -> dict

        Update club membership status of the given Club
        If True, member list will not be shown to public.
        """
        data = {
            "club_id": int(club_id),
            "is_membership_private": is_membership_private
        }
        req = requests.post(f"{self.API_URL}/update_is_membership_private", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_is_community(self, club_id, is_community=False):
        """ (Clubhouse, int, bool) -> dict

        Change room start permission. If set False, Admins can only start club rooms.
        """
        data = {
            "club_id": int(club_id),
            "is_community": is_community
        }
        req = requests.post(f"{self.API_URL}/update_is_community", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_club_description(self, club_id, description):
        """ (Clubhouse, int, str) -> dict

        Update description of the given Club
        """
        data = {
            "club_id": int(club_id),
            "description": description
        }
        req = requests.post(f"{self.API_URL}/update_club_description", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def update_club_rules(self, club_id='', rules=()):
        """ (Clubhouse, str, list) -> dict

        Update Club's rules (Maximum upto 3 rules)
        rules: [{'desc': "text", "title": "text"}, ...]
        """
        data = {
            "club_id": int(club_id),
            "rules": rules if rules else [],
        }
        req = requests.post(f"{self.API_URL}/update_club_rules", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()


class Topic(Helper):
    def __init__(self):
        super().__init__()

    def get_all_topics(self):
        """ (Clubhouse) -> dict

        Get list of topics, based on the server's channel selection algorithm
        """
        req = requests.get(f"{self.API_URL}/get_all_topics", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def get_topic(self, topic_id):
        """ (Clubhouse, int) -> dict

        Get topic's information based on the given topic id.
        """
        data = {
            "topic_id": int(topic_id)
        }
        req = requests.post(f"{self.API_URL}/get_topic", headers=self.HEADERS, json=data)
        logging.info(req)
        return req.json()

    def get_users_for_topic(self, topic_id, page_size=25, page=1):
        """ (Clubhouse, int, int, int) -> dict

        Get list of users based on the given topic id.
        """
        query = "topic_id={}&page_size={}&page={}".format(
            topic_id,
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_users_for_topic?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()

    def get_clubs_for_topic(self, topic_id, page_size=25, page=1):
        """ (Clubhouse, int, int, int) -> dict

        Get list of clubs based on the given topic id.
        """
        query = "topic_id={}&page_size={}&page={}".format(
            topic_id,
            page_size,
            page
        )
        req = requests.get(f"{self.API_URL}/get_clubs_for_topic?{query}", headers=self.HEADERS)
        logging.info(req)
        return req.json()









































