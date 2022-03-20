"""
auto_mod.py

Sample CLI Clubhouse Client

RTC: For voice communication
"""

import os
import sys
from datetime import datetime
import threading
from configparser import ConfigParser
import json

import pytz
import keyboard
from rich.table import Table
from rich.console import Console
from rich import box
import boto3

from AutoMod.mod_tools import Clubhouse


auto_mod_client = Clubhouse()
tracking_client = boto3.client('s3')

_ping_func = None
_wait_func = None
_wait_mod_func = None
_dump_func = None
_track_func = None
_announce_func = None
_wait_ping_func = None
active_mod = None
# wait_mod = True

phone_number = None
guest_list = None
mod_list = None
ping_list = None
# Load user config settings from AutoMod/mod_config.py

try:

    try:
        # Write config.ini from AutoMod/
        import AutoMod.mod_config as mod_config
    except ModuleNotFoundError:
        print("[-] 'AutoMod/mod_config.py' not found")
        print("[-] Create 'AutoMod/mod_config.py' using 'AutoMod/mod_config_template.py'")
        sys.exit(1)
    else:
        mod_config = mod_config.get_settings()
        config_object = ConfigParser()

    try:
        # Read config.ini
        config_object.read("config.ini")
    except AttributeError:
        print("[-] No 'mod_config.ini' file found in root directory")
        print("[-] Create mod_config.ini file using AutoMod/mod_config_template.ini file")
        sys.exit(1)

    try:
        # Get phone number
        userinfo = config_object["USERINFO"]
        phone_number = userinfo["phone_number"]
    except KeyError:
        print("[-] Phone number not loaded")
    else:
        print("[.] Phone number loaded")

    try:
    # Add user input to ask which mod list
        _mods = config_object["MODLIST1"]
        mod_list = []
        for mod in _mods:
            mod_list.append(_mods[mod])
    except KeyError:
        print("[-] Mod list not loaded")





        print("[.] Mod list loaded")

    # Ask which guest list
    _guests = config_object["GUESTLIST1"]
    guest_list = []
    for guest in _guests:
        guest_list.append(_guests[guest])
    print("[.] Guest list loaded")

    # Ask which ping list
    _pingers = config_object["PINGLIST"]
    ping_list = []
    for pinger in _pingers:
        ping_list.append(_pingers[pinger])
    print("[.] Ping list loaded")

except KeyError:
    pass

# Set some global variables
# Figure this out when you're ready to start playing music
try:
    import agorartc
    print("[.] Imported agorartc")
    RTC = agorartc.createRtcEngineBridge()
    eventHandler = agorartc.RtcEngineEventHandlerBase()
    RTC.initEventHandler(eventHandler)
    # 0xFFFFFFFE will exclude Chinese servers from Agora's servers.
    RTC.initialize(Clubhouse.AGORA_KEY, None, agorartc.AREA_CODE_GLOB & 0xFFFFFFFE)

    audio_recording_device_manager, err = RTC.createAudioRecordingDeviceManager()
    count = audio_recording_device_manager.getCount()
    for i in range(count):
        _audio_device = audio_recording_device_manager.getDevice(i, '', '')

        if 'BlackHole 2ch' in _audio_device[1]:
            audio_recording_device_manager.setDevice(_audio_device[2])
            audio_recording_device_manager.setDeviceVolume(50)
            print('[.] Audio recording device set to BlackHole 2ch.')
            break
        else:
            print('[-] Audio recording device not set.')

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

        print('[.] AutoMod loaded')

    else:
        print('[-] AutoMod not loaded')


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


@set_interval(300)
def announcement_5(client=auto_mod_client, channel=None, message=None):

    channel_info = client.get_channel(channel)

    if channel_info['success']:
        message = "This a test announcement that posts every 5 minutes."
        client.send_channel_message(channel, message)
    else:
        return False

    return True


@set_interval(600)
def announcement_10(client=auto_mod_client, channel=None, message=None):

    channel_info = client.get_channel(channel)

    if channel_info['success']:
        message = "This a test announcement that posts every 10 minutes."
        client.send_channel_message(channel, message)
    else:
        return False

    return True


@set_interval(1800)
def announcement_30(client=auto_mod_client, channel=None, message=None, message2=None):

    channel_info = client.get_channel(channel)

    if channel_info['success']:
        client.send_channel_message(channel, message)

        if message2:
            client.send_channel_message(channel, message2)

    else:
        return False

    return True


@set_interval(3600)
def announcement_60(client=auto_mod_client, channel=None, message=None, message2=None):

    channel_info = client.get_channel(channel)

    if channel_info['success']:
        client.send_channel_message(channel, message)

        if message2:
            client.send_channel_message(channel, message2)

    else:
        return False

    return True


@set_interval(30)
def _ping_keep_alive(client=auto_mod_client, channel=None):
    """ (str) -> bool

    Continue to ping alive every 30 seconds.
    """
    try:
        client.active_ping(channel)
    except TimeoutError:
        return False

    return True


@set_interval(10)
def _wait_speaker_permission(client=auto_mod_client, channel=None, user=None, music=False):
    """ (str) -> bool

    Function that runs when you've requested for a voice permission.
    """

    # Check if the moderator allowed your request.
    res_inv = client.accept_speaker_invite(channel, user)
    if music:
        RTC.muteLocalAudioStream(mute=False)
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


@set_interval(30)
def _wait_ping(client=auto_mod_client, status_on=active_mod, ping_list=ping_list):
    """ (str) -> bool

    Function that runs when idle.
    """

    # If not active mod
    if not status_on:

        # Check for ping.
        notifications = client.get_notifications()

        for notification in notifications['notifications']:
            if notification['type'] == 9:
                _user_id = str(notification['user_profile']['user_id'])
                _channel = notification['channel']
                _message = notification['message']
                _time_created = notification['time_created']
                _time_created = datetime.strptime(_time_created, '%Y-%m-%dT%H:%M:%S.%f%z')

                _time_now = datetime.now(pytz.timezone('UTC'))
                diff = _time_now - _time_created
                diff = diff.total_seconds()

                if diff < 30:

                    if _user_id in ping_list:
                        print('channel: ' + _channel)
                        print(_message)
                        mod_room(client, _channel, True)
                        return False

    if status_on:
        return False

    return True


def data_dump(client=auto_mod_client, channel=None):

    timestamp = datetime.now(pytz.timezone('UTC')).isoformat()

    s3_client = boto3.client('s3')
    _bucket = 'iconicbucketch'

    channel_info = client.get_channel(channel)
    if channel_info['success']:
        channel_name = channel_info['channel']

        _data = json.dumps(channel_info)
        _key = channel_name + '_' + timestamp + '.json'

        response = s3_client.put_object(
            Body=_data,
            Bucket=_bucket,
            Key=_key,
        )

        print('room dumped')

    feed_info = client.get_feed()
    if feed_info['items']:

        _data = json.dumps(feed_info)
        _key = 'feed' + '_' + timestamp + '.json'

        response = s3_client.put_object(
            Body=_data,
            Bucket=_bucket,
            Key=_key,
        )

        print('feed dumped')

    return True


@set_interval(60)
def data_dump_client(client=auto_mod_client, channel=None):

    timestamp = datetime.now(pytz.timezone('UTC')).isoformat()

    s3_client = boto3.client('s3')
    _bucket = 'iconicbucketch'

    channel_info = client.get_channel(channel)
    if channel_info['success']:
        channel_name = channel_info['channel']

        _data = json.dumps(channel_info)
        _key = channel_name + '_' + timestamp + '.json'

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
        _key = 'feed' + '_' + timestamp + '.json'

        response = s3_client.put_object(
            Body=_data,
            Bucket=_bucket,
            Key=_key,
        )

        print('feed dumped')

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


@set_interval(15)
def _invite_social_guest(client=auto_mod_client, channel=None, welcomed_list_old=None):

    try:
        timestamp = datetime.now().isoformat()
        channel_info = client.get_channel(channel)

    except TimeoutError:
        return False

    if channel_info['success']:

        user_list = channel_info['users']

        invited_list = []
        modded_list = []
        welcomed_list = []

        for _user in user_list:

            _user_id = _user['user_id']

            if str(_user_id) == client.HEADERS['CH-UserID']:
                client_user_id = _user_id
                client_mod_status = _user['is_moderator']
                break
            else:
                client_user_id = None
                client_mod_status = False

        if client_mod_status:
            for _user in user_list:

                _user_id = _user['user_id']

                if _user_id != client_user_id:

                    _user_name = _user['name']
                    _user_name_first = _user['first_name']
                    _speaker_status = _user['is_speaker']
                    _mod_status = _user['is_moderator']
                    _invite_status = _user['is_invited_as_speaker']

                    if _speaker_status is True and _mod_status is False:
                        client.make_moderator(channel, _user_id)
                        modded_list.append(_user_name)

                        if _user_id not in welcomed_list_old:

                            if _user_id != 1414736198:
                                message = "Welcome " + _user_name_first + "! 🎉"

                            else:
                                message = 'Tabi! Hello my love! 😍'

                            client.send_channel_message(channel, message)
                            welcomed_list.append(_user_name)
                            welcomed_list_old.append(_user_id)

                            if _user_id == 2247221:
                                client.send_channel_message(channel, 'First')
                                client.send_channel_message(channel, 'And furthermore, infinitesimal')

                    if _speaker_status is False and _invite_status is False:

                        client.invite_speaker(channel, _user_id)
                        invited_list.append(_user_name)

                        if _user_id != 1414736198:
                            message = "Welcome " + _user_name_first + "! 🎉"

                        else:
                            message = 'Tabi! Hello my love! 😍'

                        client.send_channel_message(channel, message)
                        welcomed_list.append(_user_name)
                        welcomed_list_old.append(_user_id)

                        if _user_id == 2247221:
                            client.send_channel_message(channel, 'First')
                            client.send_channel_message(channel, 'And furthermore, infinitesimal')

            if len(invited_list) > 0:
                print(timestamp + ' invited: ' + str(invited_list))

            if len(modded_list) > 0:
                print(timestamp + ' modded: ' + str(modded_list))

            if len(welcomed_list) > 0:
                print(timestamp + ' welcomed: ' + str(welcomed_list))

    else:
        global active_mod
        active_mod = False
        _wait_ping_func = _wait_ping(client, active_mod)
        return False

    return True


# Can this be rewritten more efficently?
@set_interval(30)
def _invite_guest(client=auto_mod_client, channel=None, guest_list=guest_list,
                  mod_list=mod_list, welcomed_list_old=None):


    if guest_list:

        try:
            timestamp = datetime.now().isoformat()
            channel_info = client.get_channel(channel)

        except TimeoutError:
            return False

        if channel_info['success']:
            user_list = channel_info['users']

            invited_list = []
            modded_list = []
            welcomed_list = []

            for _user in user_list:

                _user_id = _user['user_id']

                if str(_user_id) == client.HEADERS['CH-UserID']:
                    client_user_id = _user_id
                    client_mod_status = _user['is_moderator']
                    break
                else:
                    client_user_id = None
                    client_mod_status = False

            if client_mod_status:
                for _user in user_list:

                    _user_id = _user['user_id']

                    if _user_id != client_user_id:

                        _user_name = _user['name']
                        _user_name_first = _user['first_name']
                        _speaker_status = _user['is_speaker']
                        _mod_status = _user['is_moderator']
                        _invite_status = _user['is_invited_as_speaker']

                        if _user_id in guest_list:

                            if _speaker_status is False and _invite_status is False:
                                client.invite_speaker(channel, _user_id)
                                invited_list.append(_user_name)

                                message = "Welcome " + _user_name_first + "! 🎉"
                                client.send_channel_message(channel, message)
                                welcomed_list.append(_user_name)
                                welcomed_list_old.append(_user_id)

                        if mod_list:

                            if _user_id in mod_list:

                                if _speaker_status is True and _mod_status is False:
                                    client.make_moderator(channel, _user_id)
                                    modded_list.append(_user_name)

                                    if _user_id not in welcomed_list_old:
                                        message = "Welcome " + _user_name_first + "! 🎉"
                                        client.send_channel_message(channel, message)
                                        welcomed_list.append(_user_name)
                                        welcomed_list_old.append(_user_id)

                if len(invited_list) > 0:
                    print(timestamp + ' invited: ' + str(invited_list))

                if len(modded_list) > 0:
                    print(timestamp + ' modded: ' + str(modded_list))

                if len(welcomed_list) > 0:
                    print(timestamp + ' welcomed: ' + str(welcomed_list))

        else:
            global active_mod
            active_mod = False
            _wait_ping_func = _wait_ping(client, active_mod)
            return False

    return True


@set_interval(60)
def track_room(client=auto_mod_client, channel=None):

    join = client.join_channel(channel)

    try:
        _joined = join['users']
    except:
        return False
    #
    data_dump(client, channel)
    print('room dumped')

    _track_func = data_dump_client(client, channel)

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

    if _announce_func:
        _announce_func.set()

    if RTC:
        RTC.leaveChannel()

    global active_mod
    if active_mod:
        active_mod = False

    client.leave_channel(channel)

    print('[.] Auto Mod terminated')

    return


def mute_audio():
    RTC.muteLocalAudioStream(mute=True)

    return


def unmute_audio():
    RTC.muteLocalAudioStream(mute=False)

    return


def mod_room(client=auto_mod_client, channel=None, music=False,
             guest_list=guest_list, mod_list=mod_list):

    _client_id = client.HEADERS['CH-UserID']

    try:

        if _wait_ping_func:
            _wait_ping_func.set()

        terminate_room(client, channel)
    except:
        pass

    join = client.join_channel(channel)
    data_dump(client, channel)
    channel_info = client.get_channel(channel)

    if channel_info['success']:

        _creator_id = join['creator_user_profile_id']

        for _user in channel_info['users']:
            if _creator_id == _user['user_id']:
                _creator_name = _user['first_name']
                break

            else:
                _creator_name = ''

        client.send_channel_message(channel, "🤖 Hello " + _creator_name + "! I'm AutoMod! ")
        # client.send_channel_message(channel, "Hello, I'm AutoMod! I'm an open-source project. "
        #                                      "Visit the link in my next message to access my code.")

        data_dump(client, channel)

        # Activate pinging
        client.active_ping(channel)
        _ping_func = _ping_keep_alive(client, channel)
        _wait_func = None

        global active_mod
        active_mod = True

        if channel_info['is_private']:
            social = True
        else:
            social = False

        user_list = channel_info['users']
        for _user in user_list:
            _user_id = _user['user_id']
            _user_id = str(_user_id)

            if _user_id == _client_id:
                auto_bot_user = _user

                if not auto_bot_user['is_speaker']:
                    client.audience_reply(channel)
                    client.send_channel_message(channel, 'Please invite me to speak and make me a Moderator.')
                    _wait_func = _wait_speaker_permission(client, channel, _client_id, music)
                    # _wait_mod_func = _wait_mod_permission(client, channel, user)

                if auto_bot_user['is_speaker'] and not auto_bot_user['is_moderator']:
                    client.send_channel_message(channel, 'Please make me a Moderator.')
                    # _wait_mod_func = _wait_mod_permission(client, channel, user)
                    # global wait_mod
                    # wait_mod = True

        welcomed_list_old = []
        if social is True:

            _invite_func = _invite_social_guest(client, channel, welcomed_list_old)
            _dump_func = None
            music = True
            message = 'The share url for this room is'
            message2 = 'https://www.clubhouse.com/room/' + channel

            client.send_channel_message(channel, message)
            client.send_channel_message(channel, message2)
            _announce_func = announcement_60(client, channel, message, message2)

        if social is False:
            _invite_func = _invite_guest(client, channel, guest_list, mod_list, welcomed_list_old)
            _dump_func = data_dump_client(client, channel)

    # Check for the voice level.
    if RTC:
        token = join['token']
        # RTC.setExternalAudioSource(True, 32000, 2)
        RTC.joinChannel(token, channel, "", int(_client_id))

        if music:
            RTC.muteLocalAudioStream(mute=False)
            client.update_audio_music_mode(channel)
        else:
            RTC.muteLocalAudioStream(mute=True)

        RTC.muteAllRemoteAudioStreams(mute=True)

        print('[.] Audio Loaded')
        print('[.] Remote Audio Muted')

    else:
        print("[!] Agora SDK is not installed.")
        print("    You may not speak or listen to the conversation.")


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































