#!/usr/bin/python -u
#-*- coding: utf-8 -*-
# pylint: disable=line-too-long,too-many-arguments,too-many-lines
# pylint: disable=no-self-argument,not-callable

"""
clubhouse_mod.py
"""

import uuid
import random
import secrets
import functools
import requests

class Clubhouse:
    """
    Clubhouse Class

    Decorators:
        @require_authentication:
            - this means that the endpoint requires authentication to access.

        @unstable_endpoint
            - This means that the endpoint is never tested.
            - Likely to be endpoints that were taken from a static analysis
    """

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
        "Connection": "keep-alive",
        "Content-Type": "application/json; charset=utf-8",
        "Cookie": f"__cfduid={secrets.token_hex(21)}{random.randint(1, 9)}"
    }

    # Where do User and Device IDs come from?
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

    # def unstable_endpoint(func):
    #     """ Simple decorator to warn that this endpoint is never tested at all. """
    #     @functools.wraps(func)
    #     def wrap(self, *args, **kwargs):
    #         print("[!] This endpoint is NEVER TESTED and MAY BE UNSTABLE. BE CAREFUL!")
    #         return func(self, *args, **kwargs)
    #     return wrap

    def __init__(self, user_id='', user_token='', user_device='', headers=None):
        """ (Clubhouse, str, str, str, dict) -> NoneType
        Set authenticated information
        """
        self.HEADERS = dict(self.HEADERS)
        if isinstance(headers, dict):
            self.HEADERS.update(headers)
        self.HEADERS['CH-UserID'] = user_id if user_id else "(null)"
        if user_token:
            self.HEADERS['Authorization'] = f"Token {user_token}"
        self.HEADERS['CH-DeviceId'] = user_device.upper() if user_device else str(uuid.uuid4()).upper()

    def __str__(self):
        """ (Clubhouse) -> str
        Get information about the given class.
        >>> clubhouse = Clubhouse()
        >>> str(clubhouse)
        Clubhouse(user_id=(null), user_token=None, user_device=31525f52-6b67-40de-83c0-8f9fe0f6f409)
        """
        return "Clubhouse(user_Id={}, user_token={}, user_device={})".format(
            self.HEADERS.get('CH-UserID'),
            self.HEADERS.get('Authorization'),
            self.HEADERS.get('CH-DeviceId')
        )
    def start_phone_number_auth(self, phone_number):
        """ (Clubhouse, str) -> dict

        Begin phone number authentication.
        Some examples for the phone number.

        >>> clubhouse = Clubhouse()
        >>> clubhouse.start_phone_number_auth("+821012341337")
        ...
        >>> clubhouse.start_phone_number_auth("+818013371221")
        ...
        """
        if self.HEADERS.get("Authorization"):
            raise Exception('Already Authenticated')
        data = {
            "phone_number": phone_number
        }
        req = requests.post(f"{self.API_URL}/start_phone_number_auth", headers=self.HEADERS, json=data)
        return req.json()


    def complete_phone_number_auth(self, phone_number, rc_token, verification_code):
        """ (Clubhouse, str, str, str) -> dict

        Complete phone number authentication.
        NOTE: As of June 2021, ReCAPTCHA v3 has been introduced so you need to get that token ready...
        This should return `auth_token`, `access_token`, `refresh_token`, is_waitlisted, ...
        Please note that output may be different depending on the status of the authenticated user
        """
        if self.HEADERS.get("Authorization"):
            raise Exception('Already Authenticatied')
        data = {
            "device_token": None,
            "rc_token": rc_token,
            "phone_number": phone_number,
            "verification_code": verification_code
        }
        req = requests.post(f"{self.API_URL}/complete_phone_number_auth", headers=self.HEADERS, json=data)
        return req.json()

    def check_for_update(self, is_testflight=False):
        """ (Clubhouse, bool) -> dict

        Check for app updates.

        >>> clubhouse = Clubhouse()
        >>> clubhouse.check_for_update(False)
        {'has_update': False, 'success': True}
        """
        query = f"is_testflight={int(is_testflight)}"
        req = requests.get(f"{self.API_URL}/check_for_update?{query}", headers=self.HEADERS)
        return req.json()

    @require_authentication
    def logout(self):
        """ (Clubhouse) -> dict

        Logout from the app.
        """
        data = {}
        req = requests.post(f"{self.API_URL}/logout", headers=self.HEADERS, json=data)
        return req.json()

    @require_authentication
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
        return req.json()

    @require_authentication
    def unfollow(self, user_id):
        """ (Clubhouse, int) -> dict

        Unfollow a user.
        """
        data = {
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/unfollow", headers=self.HEADERS, json=data)
        return req.json()

    @require_authentication
    def block(self, user_id):
        """ (Clubhouse, int) -> dict

        Block a user.
        """
        data = {
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/block", headers=self.HEADERS, json=data)
        return req.json()

    @require_authentication
    def unblock(self, user_id):
        """ (Clubhouse, int) -> dict

        Unfollow a user.
        """
        data = {
            "user_id": int(user_id)
        }
        req = requests.post(f"{self.API_URL}/unblock", headers=self.HEADERS, json=data)
        return req.json()

    @require_authentication
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
        return req.json()


