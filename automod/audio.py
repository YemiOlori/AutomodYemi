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

from . import moderation as mod

auto_mod_client = mod.ModClient()

# Set some global variables
# Figure this out when you're ready to start playing music
try:
    import agorartc
    logging.info("Imported agorartc")
    RTC = agorartc.createRtcEngineBridge()
    eventHandler = agorartc.RtcEngineEventHandlerBase()
    RTC.initEventHandler(eventHandler)
    # 0xFFFFFFFE will exclude Chinese servers from Agora's servers.
    RTC.initialize(mod.ModClient.AGORA_KEY, None, agorartc.AREA_CODE_GLOB & 0xFFFFFFFE)

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



