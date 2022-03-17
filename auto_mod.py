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
from rich import box
from AutoMod.mod_tools import Clubhouse
import datetime
import boto3
import json

auto_mod_client = Clubhouse()
tracking_client = boto3.client('s3')

_ping_func = None
_wait_func = None
_wait_mod_func = None
_dump_func = None
_track_func = None
wait_mod = True

# Need to figure out how to run "mod_settings" module when app starts
phone_number = None
guest_list = None
mod_list = None
try:
    # Read config.ini file
    config_object = ConfigParser()
    config_object.read("config.ini")

    # Get the password
    userinfo = config_object["USERINFO"]
    phone_number = userinfo["phone_number"]
    print("[.] Phone number loaded")

    # Ask which mod list
    _mods = config_object["MODLIST1"]
    mod_list = []
    for mod in _mods:
        mod_list.append(_mods[mod])
    print("[.] Mod list loaded")

    # Ask which guest list
    _guests = config_object["GUESTLIST1"]
    guest_list = []
    for guest in _guests:
        guest_list.append(_guests[guest])
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


def login(client=auto_mod_client):

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


def reload_user(client=auto_mod_client):
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

        print('[.] Auto Mod Loaded')

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
                        print('stop: ' + str(func))
                        break

            thread = threading.Thread(target=loop)
            thread.daemon = True
            thread.start()
            print('start: ' + str(func))

            return stopped

        return wrap

    return decorator


@set_interval(30)
def _ping_keep_alive(client=auto_mod_client, channel=None):
    """ (str) -> bool

    Continue to ping alive every 30 seconds.
    """
    client.active_ping(channel)
    return True


@set_interval(10)
def _wait_speaker_permission(client=auto_mod_client, channel=None, user=None):
    """ (str) -> bool

    Function that runs when you've requested for a voice permission.
    """

    # Check if the moderator allowed your request.
    res_inv = client.accept_speaker_invite(channel, user)
    if res_inv['success']:
        return False

    return True


# @set_interval(10)
# def _wait_mod_permission(client=auto_mod_client, channel=None, user=None):
#     """ (str) -> bool
#
#     Function that runs when you've requested for a voice permission.
#     """
#
#     # Check if the moderator allowed your request.
#     channel_info = client.get_channel(channel)
#     if channel_info['success']:
#         user_list = channel_info['users']
#         for _user in user_list:
#             if _user['user_id'] == user:
#                 if _user['is_moderator']:
#                     global wait_mod
#                     wait_mod = False
#                     return False
#
#     return True


def data_dump(client=auto_mod_client, channel=None):

    timestamp = datetime.datetime.now()
    date = timestamp.date()
    time = timestamp.time()
    time_str = str(date) + '_' + str(time)

    s3_client = boto3.client('s3')
    _bucket = 'iconicbucketch'

    channel_info = client.get_channel(channel)
    if channel_info['success']:
        channel_name = channel_info['channel']

        _data = json.dumps(channel_info)
        _key = channel_name + '_' + time_str + '.json'

        response = s3_client.put_object(
            Body=_data,
            Bucket=_bucket,
            Key=_key,
        )

    feed_info = client.get_feed()
    if feed_info['items']:

        _data = json.dumps(feed_info)
        _key = 'feed' + '_' + time_str + '.json'

        response = s3_client.put_object(
            Body=_data,
            Bucket=_bucket,
            Key=_key,
        )

    print('data dumped')

    return True


@set_interval(60)
def data_dump_client(client=auto_mod_client, channel=None):

    timestamp = datetime.datetime.now()
    date = timestamp.date()
    time = timestamp.time()
    time_str = str(date) + '_' + str(time)

    s3_client = boto3.client('s3')
    _bucket = 'iconicbucketch'

    channel_info = client.get_channel(channel)
    if channel_info['success']:
        channel_name = channel_info['channel']

        _data = json.dumps(channel_info)
        _key = channel_name + '_' + time_str + '.json'

        response = s3_client.put_object(
            Body=_data,
            Bucket=_bucket,
            Key=_key,
        )

        print('room dumped')

    else:
        return False

    feed_info = client.get_feed()
    if feed_info['items']:

        _data = json.dumps(feed_info)
        _key = 'feed' + '_' + time_str + '.json'

        response = s3_client.put_object(
            Body=_data,
            Bucket=_bucket,
            Key=_key,
        )

        print('feed dumped')

    else:
        return False

    return True


# Can this be rewritten more efficently?
@set_interval(30)
def _invite_guest(client=auto_mod_client, channel=None, guest_list=guest_list,
                  mod_list=mod_list, already_invited=None):

    if guest_list:

        channel_info = client.get_channel(channel)

        if channel_info['success']:
            user_list = channel_info['users']

            invited_list = []
            modded_list = []

            for _user in user_list:
                _user_id = _user['user_id']
                _speaker_status = _user['is_speaker']
                _mod_status = _user['is_moderator']
                _invite_status = _user['is_invited_as_speaker']

                if _user_id in guest_list:

                    if _speaker_status is True and _mod_status is False:
                        client.make_moderator(channel, _user_id)
                        modded_list.append(_user_name)
                        print('modded: ' + str(modded_list))

                    if _speaker_status is False and _invite_status is False:
                        client.invite_speaker(channel, _user_id)
                        invited_list.append(_user_name)
                        print('invited: ' + str(invited_list))

            print('scan complete')


        else:
            return False

    return True


@set_interval(15)
def _invite_social_guest(client=auto_mod_client, channel=None):

    channel_info = client.get_channel(channel)

    if channel_info['success']:
        user_list = channel_info['users']

        invited_list = []
        modded_list = []

        for _user in user_list:
            _user_id = _user['user_id']
            _user_name = _user['name']
            _speaker_status = _user['is_speaker']
            _mod_status = _user['is_moderator']
            _invite_status = _user['is_invited_as_speaker']

            if _speaker_status is True and _mod_status is False:
                client.make_moderator(channel, _user_id)
                modded_list.append(_user_name)
                print('modded: ' + str(modded_list))

            if _speaker_status is False and _invite_status is False:
                client.invite_speaker(channel, _user_id)
                invited_list.append(_user_name)
                print('invited: ' + str(invited_list))

        print('scan complete')

    else:
        return False

    return True


def get_hallway(client, max_limit=30):

    # Get channels and print
    console = Console(width=180)
    table = Table(show_header=True, header_style="bold magenta", box=box.MINIMAL_HEAVY_HEAD, leading=True)
    table.add_column("speakers", width=8, justify='center')
    table.add_column("users", width=8, justify='center')
    table.add_column("type", width=8)
    table.add_column("channel", width=10)
    table.add_column("club", width=35, no_wrap=True)
    table.add_column("title", style="cyan", width=70)

    feed = client.get_feed()

    channel_list = []
    for feed_item in feed['items']:

        key = feed_item.keys()
        if 'channel' in key:
            channel_list.append(feed_item)

    i = 0
    for channel in channel_list:
        channel = channel['channel']

        i += 1
        if i > max_limit:
            break

        channel_type = ''
        club = ''

        if channel['is_social_mode']:
            channel_type = "social"

        if channel['is_private']:
            channel_type = "private"

        if channel['club']:
            club = channel['club']['name']

        table.add_row(
            str(int(channel['num_speakers'])),
            str(int(channel['num_all'])),
            str(channel_type),
            str(channel['channel']),
            str(club),
            str(channel['topic']),
        )

    console.print(table)

    return


@set_interval(60)
def track_room(client=auto_mod_client, channel=None):

    join = client.join_channel(channel)
    if join['users']:
        data_dump(client, channel)

        _track_func = data_dump_client(client, channel)

    else:
        return False

    return True


def terminate_room(client=auto_mod_client, channel=None):

    if _ping_func:
        _ping_func.set()

    if _wait_func:
        _wait_func.set()

    if _wait_mod_func:
        _wait_mod_func.set()

    if _dump_func:
        _dump_func.set()

    if _track_func:
        _track_func.set()

    if RTC:
        RTC.leaveChannel()

    client.leave_channel(channel)

    print('[.] Auto Mod terminated')

    return


def mod_room(client=auto_mod_client, channel=None, social=False,
             guest_list=guest_list, mod_list=mod_list):

    user = client.HEADERS['CH-UserID']

    try:
        terminate_mod_room(client, channel)
    except:
        pass

    join = client.join_channel(channel)

    data_dump(client, channel)

    user_list = join['users']
    for _user in user_list:
        _user_id = _user['user_id']
        _user_id = str(_user_id)

        if _user_id == _user_id:
            auto_bot_user = _user

            if auto_bot_user['is_speaker'] and not auto_bot_user['is_moderator']:
                client.send_channel_message(channel, 'Please make me a Moderator')
                # _wait_mod_func = _wait_mod_permission(client, channel, user)
                # global wait_mod
                # wait_mod = True

            elif not auto_bot_user['is_speaker']:
                client.audience_reply(channel)
                client.send_channel_message(channel, 'Please invite me to speak and make me a Moderator')
                _wait_func = _wait_speaker_permission(client, channel, user)
                # _wait_mod_func = _wait_mod_permission(client, channel, user)

    if social is False:
        _invite_func = _invite_guest(client, channel, guest_list, mod_list)
        _dump_func = data_dump_client(client, channel)

    if social is True:
        _invite_func = _invite_social_guest(client, channel)
        _dump_func = None

    # Activate pinging
    client.active_ping(channel)
    _ping_func = _ping_keep_alive(client, channel)
    _wait_func = None

    # if keyboard.is_pressed('q'):  # if key 'q' is pressed
    #     print("You've terminated Auto Mod!")
    #
    #     if _ping_func:
    #         _ping_func.set()
    #
    #     if _wait_func:
    #         _wait_func.set()
    #
    #     if _dump_func:
    #         _dump_func.set()
    #
    #     if RTC:
    #         RTC.leaveChannel()
    #
    #
    #     client.leave_channel(channel)

    return































