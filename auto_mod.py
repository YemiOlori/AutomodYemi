"""
cli.py

Sample CLI Clubhouse Client

RTC: For voice communication
"""

import os
import sys
import threading
from configparser import ConfigParser
import keyboard
from rich.table import Table
from rich.console import Console
from AutoMod.mod_tools import Clubhouse
import yaml
import time

client = Clubhouse()


# Need to figure out how to run "mod_settings" module when app starts
phone_number = None
try:
    # Read config.ini file
    config_object = ConfigParser()
    config_object.read("config.ini")

    # Get the password
    userinfo = config_object["USERINFO"]
    phone_number = userinfo["phone_number"]
    print("[.] Phone number loaded")

    # Ask which guest list
    guest_list = config_object["GUESTLIST1"]
    guests = []
    for guest in guest_list:
        guests.append(guest_list[guest])
    print("[.] Guest list loaded")

except: # need more specific exception clause
    pass


# Set some global variables
# Figure this out when you're ready to start playing music
try:
    import agorartc
    RTC = agorartc.createRtcEngineBridge()
    eventHandler = agorartc.RtcEngineEventHandlerBase()
    RTC.initEventHandler(eventHandler)
    # 0xFFFFFFFE will exclude Chinese servers from Agora's servers.
    RTC.initialize(Clubhouse.AGORA_KEY, None, agorartc.AREA_CODE_GLOB & 0xFFFFFFFE)
    # Enhance voice quality
    if RTC.setAudioProfile(
            agorartc.AUDIO_PROFILE_MUSIC_HIGH_QUALITY_STEREO,
            agorartc.AUDIO_SCENARIO_GAME_STREAMING
        ) < 0:
        print("[-] Failed to set the high quality audio profile")
except ImportError:
    RTC = None


def write_config(user_id, user_token, user_device, refresh_token, access_token,
                 filename='setting.ini'):
    """ (str, str, str, str) -> bool

    Write Config. return True on successful file write
    """
    config = ConfigParser()
    config["Account"] = {
        "user_device": user_device,
        "user_id": user_id,
        "user_token": user_token,
        "refresh_token": refresh_token,
        "access_token": access_token
    }
    with open(filename, 'w') as config_file:
        config.write(config_file)
    return True


def read_config(filename='setting.ini'):
    """ (str) -> dict of str

    Read Config
    """
    config = ConfigParser()
    config.read(filename)
    if "Account" in config:
        return dict(config['Account'])
    return dict()


def login(client=client):

    rc_token = None

    user_phone_number = phone_number if phone_number else \
        input("[.] Please enter your phone number. (+818043217654) > ")

    result = client.start_phone_number_auth(user_phone_number)
    if not result['success']:
        print(f"[-] Error occurred during authentication. ({result['error_message']})")

    verification_code = input("[.] Please enter the SMS verification code (123456, 000000, ...) > ")
    if isinstance(verification_code, int):
        verification_code = str(verification_code)

    result = client.complete_phone_number_auth(user_phone_number, rc_token, verification_code)
    if not result['success']:
        print(f"[-] Error occurred during authentication. ({result['error_message']})")

    user_id = result['user_profile']['user_id']
    user_token = result['auth_token']
    user_device = client.HEADERS.get("CH-DeviceId")
    refresh_token = result['refresh_token']
    access_token = result['access_token']
    write_config(user_id, user_token, user_device, refresh_token, access_token)

    print("[.] Writing configuration file complete.")

    client = Clubhouse(
        user_id=user_id,
        user_token=user_token,
        user_device=user_device,
    )

    return client

def reload_user(client=client):
    user_config = read_config()
    user_id = user_config.get('user_id')
    user_token = user_config.get('user_token')
    user_device = user_config.get('user_device')
    refresh_token = user_config.get('refresh_token')
    access_token = user_config.get('access_token')

    # Check if user is authenticated
    if user_id and user_token and user_device:
        client = Clubhouse(
            user_id=user_id,
            user_token=user_token,
            user_device=user_device
        )

    return client


def set_interval(interval):
    """ (int) -> decorator

    set_interval decorator
    """
    def decorator(func):
        def wrap(*args, **kwargs):
            stopped = threading.Event()
            def loop():
                while not stopped.wait(interval):
                    ret = func(*args, **kwargs)
                    if not ret:
                        break
            thread = threading.Thread(target=loop)
            thread.daemon = True
            thread.start()
            return stopped
        return wrap
    return decorator


@set_interval(30)
def _ping_keep_alive(client, room_id):
    """ (str) -> bool

    Continue to ping alive every 30 seconds.
    """
    client.active_ping(room_id)
    return True


@set_interval(10)
def _wait_speaker_permission(client, room_id, user_id):
    """ (str) -> bool

    Function that runs when you've requested for a voice permission.
    """

    # Check if the moderator allowed your request.
    res_inv = client.accept_speaker_invite(room_id, user_id)
    if res_inv['success']:
        return False

    return True


def join_mod_room(client=client, room_id=str):

    join = client.join_channel(channel=room_id)
    user_list = join['users']
    user_id = client.HEADERS['CH-UserID']

    for _user in user_list:
        _user_id = _user['user_id']
        _user_id = str(_user_id)

        if _user_id == user_id:
            auto_bot_user = _user

            if not auto_bot_user['is_speaker']:
                client.audience_reply(channel=room_id)

    _wait_func = _wait_speaker_permission(client, room_id, user_id)

    # Activate pinging
    client.active_ping(room_id)
    _ping_func = _ping_keep_alive(client, room_id)
    _wait_func = None

    return




























