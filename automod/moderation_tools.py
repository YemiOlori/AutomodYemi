"""
moderation_tools.py

RTC: For voice communication
"""

import os
import sys
import logging
import threading
import json
from datetime import datetime
from configparser import ConfigParser

import pytz
import keyboard
from rich.table import Table
from rich.console import Console
from rich import box
import boto3

from .clubhouse_api import Clubhouse
from . import globals

auto_mod_client = Clubhouse()
tracking_client = boto3.client('s3')

active_mod = None
_dump_func = None
_track_func = None
_wait_speak_func = None
_wait_mod_func = None
_announce_func = None
_wait_ping_func = None
_ping_active_func = None
# wait_mod = True

phone_number = None
guest_list = None
mod_list = None
ping_list = None


# Rewrite this function so that it's not redundant with 'read_config
def read_user_config(file_path, section):
    """
    The function to read the configuration parameters from the relevant section in the config file.

    :param file_path: the name of the file that will be read.
    :param section: The section of the file has to be read.
    :return section_content: Dictionary with the section parameters.
    :rtype: Dictionary
    """
    # create parser and read configuration file
    parser = ConfigParser()
    parser.read(file_path)

    section_content = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            section_content[item[0]] = item[1]
    else:
        raise Exception(f"Error in fetching config in read_config method. {section} not found in {file_path}")
        # raise Exception('Error in fetching config in read_config method. {0} not found in \
        #  {1}'.format(section, file_path))

    return section_content


def set_logging_basics(config_dict):
    """
    The function to set the logging information.
    :param config_dict: dictionary with details of configuration
    :return: None
    """
    file = config_dict.get('file')
    level = config_dict.get('level')
    logging.basicConfig(filename=file
                        , filemode='a'
                        , format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                        , level=level)

# Hardcoding the name of config file and section. This would be part of Global variable file
MASTER_FILE = 'config.ini'
LOGGER_SECTION = 'LOGGER'
logger_details = read_user_config(MASTER_FILE, LOGGER_SECTION)
set_logging_basics(logger_details)

# Load user config settings from AutoMod/mod_config.py
try:
    # Read config.ini
    config_object = ConfigParser()
    config_object.read("config.ini")
except AttributeError:
    logging.warning("No 'mod_config.ini' file found in root directory")
    sys.exit(1)
else:
    try:
        # Get phone number
        userinfo = config_object["USERINFO"]
        phone_number = userinfo["phone_number"]
    except KeyError:
        logging.info("No 'phone_number' in config.ini")
        phone_number = input("[.] Please enter your phone number. (+818043217654) > ")
    else:
        logging.info("Loaded phone number")

    try:
        # Add user input to ask which mod list
        _mods = config_object["MODLIST1"]
        mod_list = []
        for mod in _mods:
            mod_list.append(_mods[mod])
    except KeyError:
        logging.info("No 'MODLIST' in config.ini")
    else:
        logging.info("Loaded mod list")

    try:
        # Add user input to ask which guest list
        _guests = config_object["GUESTLIST1"]
        guest_list = []
        for guest in _guests:
            guest_list.append(_guests[guest])
    except KeyError:
        logging.info("No 'GUESTLIST' in config.ini")
    else:
        logging.info("Loaded guest list")

    try:
        # Ask which ping list
        _pingers = config_object["PINGLIST"]
        ping_list = []
        for pinger in _pingers:
            ping_list.append(_pingers[pinger])
    except KeyError:
        logging.info("No 'PINGLIST' in config.ini")
    else:
        logging.info("Loaded ping list")

# Set some global variables
# Figure this out when you're ready to start playing music
try:
    import agorartc
    logging.info("Imported agorartc")
    RTC = agorartc.createRtcEngineBridge()
    eventHandler = agorartc.RtcEngineEventHandlerBase()
    RTC.initEventHandler(eventHandler)
    # 0xFFFFFFFE will exclude Chinese servers from Agora's servers.
    RTC.initialize(Clubhouse.AGORA_KEY, None, agorartc.AREA_CODE_GLOB & 0xFFFFFFFE)

    audio_recording_device_manager, err = RTC.createAudioRecordingDeviceManager()
    count = audio_recording_device_manager.getCount()

    audio_recording_device_result = False
    for i in range(count):
        _audio_device = audio_recording_device_manager.getDevice(i, '', '')
        if 'BlackHole 2ch' in _audio_device[1]:
            audio_recording_device_manager.setDevice(_audio_device[2])
            audio_recording_device_manager.setDeviceVolume(50)
            audio_recording_device_result = True
            logging.info("Audio recording device set to BlackHole 2ch")
            break
    if not audio_recording_device_result:
        logging.warning("Audio recording device not set")

    # Enhance voice quality
    if RTC.setAudioProfile(
            agorartc.AUDIO_PROFILE_MUSIC_HIGH_QUALITY_STEREO,
            agorartc.AUDIO_SCENARIO_GAME_STREAMING
        ) < 0:
        logging.warning("Failed to set the high quality audio profile")

except ImportError:
    RTC = None


def read_config(filename='setting.ini'):
    """ (str) -> dict of str

    Read Config
    """
    config = ConfigParser()
    config.read(filename)

    if "Account" in config:
        return dict(config['Account'])

    return dict()


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


def login(client=auto_mod_client):
    """
    A function to login to Clubhouse.

    :param client: A Clubhouse object
    :return client: A Clubhouse object updated with authentication response
    """
    rc_token = None

    _phone_number = phone_number if phone_number else \
        input("[.] Please enter your phone number. (+818043217654) > ")

    result = client.start_phone_number_auth(_phone_number)
    if not result['success']:
        print(f"[-] Error occurred during authentication. ({result['error_message']})")

    verification_code = input("[.] Please enter the SMS verification code (123456, 000000, ...) > ")
    if isinstance(verification_code, int):
        verification_code = str(verification_code)

    result = client.complete_phone_number_auth(_phone_number, rc_token, verification_code)
    if not result['success']:
        print(f"[-] Error occurred during authentication. ({result['error_message']})")

    user_id = result['user_profile']['user_id']
    user_token = result['auth_token']
    user_device = client.HEADERS.get("CH-DeviceId")
    refresh_token = result['refresh_token']
    access_token = result['access_token']
    write_config(user_id, user_token, user_device, refresh_token, access_token)

    logging.info("Writing configuration file successful")

    client = Clubhouse(
        user_id=user_id,
        user_token=user_token,
        user_device=user_device,
    )

    return client


def reload_user(client=auto_mod_client):
    """
    A function to reload Clubhouse client from previous session.

    :param client: A Clubhouse object
    :return client: A Clubhouse object updated with configuration information
    """
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
        logging.info("Loaded AutoMod")
    else:
        logging.info("Failed to load AutoMod")

    return client


def set_interval(interval, _client=None, _channel=None, _message=None):
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
                        logging.info(f"Stopped: {func}")
                        break

            thread = threading.Thread(target=loop)
            thread.daemon = True
            thread.start()
            logging.info(f"Started: {func}")

            return stopped

        return wrap

    return decorator


@set_interval(30)
def _ping_keep_alive(client, channel=None):
    """ (str) -> bool

    Continue to ping alive every 30 seconds.
    """
    try:
        client.active_ping(channel)
    except TimeoutError:
        return False

    return True


# Figure out how to input the announcement interval
def set_announcement(client, channel, message, interval):

    @set_interval(interval, _client=client, _channel=channel, _message=message)
    def announcement(_client, _channel, _message):

        channel_info = client.get_channel(channel)

        if channel_info['success']:
            if isinstance(message, str):
                client.send_channel_message(channel, message)
            if isinstance(message, list):
                for m in message:
                    client.send_channel_message(channel, m)
        else:
            return False

        return True


# @set_interval(300)
# def announcement_5(client, channel=None, message=None):
#
#     channel_info = client.get_channel(channel)
#
#     if channel_info['success']:
#         message = "This a test announcement that posts every 5 minutes."
#         client.send_channel_message(channel, message)
#     else:
#         return False
#
#     return True
#
#
# @set_interval(600)
# def announcement_10(client, channel=None, message=None):
#
#     channel_info = client.get_channel(channel)
#
#     if channel_info['success']:
#         message = "This a test announcement that posts every 10 minutes."
#         client.send_channel_message(channel, message)
#     else:
#         return False
#
#     return True
#
#
# @set_interval(1800)
# def announcement_30(client, channel=None, message=None, message2=None):
#
#     channel_info = client.get_channel(channel)
#
#     if channel_info['success']:
#         client.send_channel_message(channel, message)
#
#         if message2:
#             client.send_channel_message(channel, message2)
#
#     else:
#         return False
#
#     return True
#
#
# @set_interval(3600)
# def announcement_60(client, channel=None, message=None, message2=None):
#
#     channel_info = client.get_channel(channel)
#
#     if channel_info['success']:
#         client.send_channel_message(channel, message)
#
#         if message2:
#             client.send_channel_message(channel, message2)
#
#     else:
#         return False
#
#     return True


@set_interval(10)
def _wait_speaker_permission(client, channel, user, music=False):
    """ (str) -> bool

    Function that runs when you've requested for a voice permission.
    """

    # Check if the moderator allowed your request.
    res_inv = client.accept_speaker_invite(channel, user)
    if res_inv['success']:
        if music:
            RTC.muteLocalAudioStream(mute=False)
            logging.info("Enabled local audio stream")
        else:
            RTC.muteLocalAudioStream(mute=True)
            logging.info("Disabled local audio stream")

        return False

    return True


# @set_interval(10)
# def _wait_mod_permission(_client, channel=None, user=None):
#     """ (str) -> bool
#
#     Function that runs when you've requested for a voice permission.
#     """
#
#     # Check if the moderator allowed your request.
#     channel_info = _client.get_channel(channel)
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


def data_dump(data, key):

    s3_client = boto3.client('s3')
    bucket = 'iconicbucketch'
    timestamp = datetime.now(pytz.timezone('UTC')).isoformat()
    data = json.dumps(data)
    key = f"{key}_{timestamp}.json"
    # key = key + '_' + timestamp + '.json'

    s3_client.put_object(
        Body=data,
        Bucket=bucket,
        Key=key,
    )

    return


def data_dump_channel(client, channel):
    channel_info = client.get_channel(channel)
    if channel_info['success']:
        channel_name = channel_info['channel']
        data = channel_info
        key = channel_name

        data_dump(data, key)
        logging.info("Successful channel dump")

    else:
        logging.info("Failed channel dumped")
        return False

    return True


def data_dump_feed(client):
    feed_info = client.get_feed()
    if feed_info['items']:
        data = feed_info
        key = 'feed'

        data_dump(data, key)
        logging.info("Successful feed dump")

    else:
        logging.info("Failed feed dumped")
        return False

    return True


@set_interval(60)
def data_dump_client(client, channel):

    data_dump_channel(client, channel)
    data_dump_feed(client)

    return


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
def _invite_social_guest(client, channel, welcomed_list_old=None):

    timestamp = datetime.now().isoformat()
    channel_info = 'No channel info'
    try:
        channel_info = client.get_channel(channel)
    except TimeoutError:
        logging.info(channel_info)
        return False

    if channel_info['success']:

        user_list = channel_info['users']

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
            logging.info('AutoMod is a moderator')

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
                        logging.info(f"AutoMod made {_user_name} a moderator")

                        if _user_id not in welcomed_list_old:
                            logging.info(f"{_user_name} has not yet been welcomed")

                            if _user_id != 1414736198:
                                message = "Welcome " + _user_name_first + "! 🎉"

                            else:
                                message = 'Tabi! Hello my love! 😍'
                                logging.info('Sent Tabitha welcome message')

                            client.send_channel_message(channel, message)
                            logging.info(f"AutoMod welcomed {_user_name}")

                            if _user_id == 2247221:
                                client.send_channel_message(channel, 'First')
                                client.send_channel_message(channel, 'And furthermore, infinitesimal')
                                logging.info('Sent Bonnie welcome message')

                    if _speaker_status is False and _invite_status is False:

                        client.invite_speaker(channel, _user_id)
                        logging.info(f"AutoMod invited {_user_name} to speak")

                        if _user_id != 1414736198:
                            message = "Welcome " + _user_name_first + "! 🎉"

                        else:
                            message = 'Tabi! Hello my love! 😍'
                            logging.info('Sent Tabitha welcome message')

                        client.send_channel_message(channel, message)
                        logging.info(f"AutoMod welcomed {_user_name}")

                        if _user_id == 2247221:
                            client.send_channel_message(channel, 'First')
                            client.send_channel_message(channel, 'And furthermore, infinitesimal')
                            logging.info('Sent Bonnie welcome message')

    else:
        global active_mod
        active_mod = False
        logging.info("Changed active_mod to False")
        global _wait_ping_func
        _wait_ping_func = listen_channel_ping(client, active_mod)
        logging.info('Enabled listen_channel_ping')
        return False

    return True


# Can this be rewritten more efficently?
@set_interval(30)
def _invite_guest(client, channel=None, guest_list=guest_list,
                  mod_list=mod_list, welcomed_list_old=None):

    if guest_list:

        try:
            timestamp = datetime.now().isoformat()
            channel_info = client.get_channel(channel)

        except TimeoutError:
            return False

        if channel_info['success']:
            user_list = channel_info['users']

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
                                logging.info(f"AutoMod invited {_user_name} to speak")

                                message = "Welcome " + _user_name_first + "! 🎉"
                                client.send_channel_message(channel, message)
                                logging.info(f"AutoMod welcomed {_user_name}")

                        if mod_list:

                            if _user_id in mod_list:

                                if _speaker_status is True and _mod_status is False:
                                    client.make_moderator(channel, _user_id)
                                    logging.info(f"AutoMod made {_user_name} a moderator")

                                    if _user_id not in welcomed_list_old:
                                        message = "Welcome " + _user_name_first + "! 🎉"
                                        client.send_channel_message(channel, message)
                                        welcomed_list_old.append(_user_id)
                                        logging.info(f"AutoMod welcomed {_user_name}")


        else:
            global active_mod
            active_mod = False
            global _wait_ping_func
            _wait_ping_func = listen_channel_ping(client, active_mod)
            return False

    return True


@set_interval(60)
def track_room(client, channel=None):

    join = client.join_channel(channel)

    try:
        _joined = join['users']
    except:
        return False
    #
    data_dump_channel(client, channel)
    print('room dumped')

    _track_func = data_dump_client(client, channel)

    return True


def terminate_room(client, channel=None):

    if _ping_active_func:
        _ping_active_func.set()

    if _wait_speak_func:
        _wait_speak_func.set()

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


def mod_room(client, channel=None, music=False,
             guest_list=guest_list, mod_list=mod_list):

    _client_id = client.HEADERS['CH-UserID']

    try:

        if _wait_ping_func:
            _wait_ping_func.set()

        terminate_room(client, channel)
    except:
        pass

    join = client.join_channel(channel)
    data_dump_channel(client, channel)
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

        data_dump_channel(client, channel)

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
            messages = [message, message2]

            client.send_channel_message(channel, message)
            client.send_channel_message(channel, message2)
            _announce_func = set_announcement(client, channel, messages, 90)

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


@set_interval(30)
def listen_channel_ping(client, active_mod=active_mod, ping_list=ping_list):
    """ (str) `-> bool

    Function that runs when idle.
    """

    # If not active mod
    if not active_mod:

        # Check for ping.
        notifications = client.get_notifications()

        for notification in notifications['notifications']:
            if notification['type'] == 9:
                _user_id = str(notification['user_profile']['user_id'])
                _channel = notification['channel']
                _message = notification['message']

                time_created = notification['time_created']
                time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
                time_now = datetime.now(pytz.timezone('UTC'))
                time_diff = time_now - time_created
                time_diff = time_diff.total_seconds()

                if time_diff < 30:
                    if _user_id in ping_list:
                        logging.info(f"Channel: {_channel} - {_message}")
                        # logging.info("Channel: " + _channel + " - " _message)
                        mod_room(client, _channel, True)
                        return False

    if active_mod:
        return False

    return True








