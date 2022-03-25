"""
auto_mod_cli.py

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

from .clubhouse import Clubhouse
from . import moderation as mod_tools

auto_mod_client = Clubhouse()


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
    folder = config_dict.get('folder')
    file = config_dict.get('file')
    level = config_dict.get('level')
    filemode = config_dict.get('filemode')
    logging.basicConfig(
        filename=f"{folder}{file}",
        filemode=filemode,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=level)


# Hardcoding the name of config file and section. This would be part of Global variable file
MASTER_FILE = '/Users/deon/Documents/GitHub/HQ/config.ini'
LOGGER_SECTION = 'Logger'
logger_details = read_user_config(MASTER_FILE, LOGGER_SECTION)
set_logging_basics(logger_details)


def load_phone_number():
    try:
        # Read config.ini
        config_object = ConfigParser()
        config_object.read("/Users/deon/Documents/GitHub/HQ/config.ini")
    except AttributeError:
        logging.warning("auto_mood_cli.load_phone_number No 'mod_config.ini' file found in root directory")
        sys.exit(1)
    else:
        try:
            # Get phone number
            userinfo = config_object["Account"]
            phone_number = userinfo["phone_number"]
        except KeyError:
            logging.info("auto_mood_cli.load_phone_number No 'phone_number' in config.ini")
            phone_number = input("[.] Please enter your phone number. (+818043217654) > ")
        else:
            logging.info("auto_mood_cli.load_phone_number Loaded phone number")

    return phone_number


phone_number = load_phone_number()


# Set some global variables
# Figure this out when you're ready to start playing music
try:
    import agorartc
    logging.info("automod.load_agora Imported agorartc")
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
            logging.info("auto_mod_cli.load_agora Audio recording device set to BlackHole 2ch")
            break
    if not audio_recording_device_result:
        logging.warning("auto_mod_cli.load_agora Audio recording device not set")

    # Enhance voice quality
    if RTC.setAudioProfile(
            agorartc.AUDIO_PROFILE_MUSIC_HIGH_QUALITY_STEREO,
            agorartc.AUDIO_SCENARIO_GAME_STREAMING
        ) < 0:
        logging.warning("auto_mod_cli.load_agora Failed to set the high quality audio profile")

except ImportError:
    RTC = None


def read_internal_config(filename='/Users/deon/Documents/GitHub/HQ/setting.ini'):
    """ (str) -> dict of str

    Read Config
    """
    config = ConfigParser()
    config.read(filename)

    if "Account" in config:
        return dict(config['Account'])

    return dict()


def write_internal_config(user_id, user_token, user_device, refresh_token, access_token,
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
        logging.warning(f"auto_mod_cli.login Error occurred during authentication. ({result['error_message']})")

    verification_code = input("[.] Please enter the SMS verification code (123456, 000000, ...) > ")
    if isinstance(verification_code, int):
        verification_code = str(verification_code)

    result = client.complete_phone_number_auth(_phone_number, rc_token, verification_code)
    if not result['success']:
        logging.warning(f"auto_mod_cli.login occurred during authentication. ({result['error_message']})")

    user_id = result['user_profile']['user_id']
    user_token = result['auth_token']
    user_device = client.HEADERS.get("CH-DeviceId")
    refresh_token = result['refresh_token']
    access_token = result['access_token']
    write_internal_config(user_id, user_token, user_device, refresh_token, access_token)

    logging.info("auto_mod_cli.login Writing configuration file successful")

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
    user_config = read_internal_config()
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
        logging.info("auto_mod_cli.reload_user Reload client successful")
    else:
        logging.info("auto_mod_cli.reload_user Reload client not successful")

    return client


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


def mute_audio():
    RTC.muteLocalAudioStream(mute=True)
    return


def unmute_audio():
    RTC.muteLocalAudioStream(mute=False)
    return


def start_music(client, channel, task=None, announcement=None, interval=3600):

    join_dict = mod_tools.automation(client, channel, task, announcement, interval)

    # Check for the voice level.
    if RTC:
        token = join_dict['token']
        RTC.joinChannel(token, channel, "", int(mod_tools.Var.client_id))

        RTC.muteLocalAudioStream(mute=False)
        client.update_audio_music_mode(channel)
        RTC.muteAllRemoteAudioStreams(mute=True)

        logging.info("auto_mod_cli.music_room RTC audio loaded")
        logging.info("auto_mod_cli.music_room RTC remote audio muted")

    else:
        logging.warning("logging.info Agora SDK is not installed.")

    return


def terminate_music(client, channel):

    mod_tools.termination(client, channel)

    if RTC:
        RTC.leaveChannel()

    return



