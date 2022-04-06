"""
auto_mod_cli.py

RTC: For voice communication
"""

# import os
# import sys
import logging

from .clubhouse import Clubhouse


class AudioClient:

    AGORA_KEY = Clubhouse.AGORA_KEY

    try:
        import agorartc
        logging.info("Imported agorartc")
        RTC = agorartc.createRtcEngineBridge()
        eventHandler = agorartc.RtcEngineEventHandlerBase()
        RTC.initEventHandler(eventHandler)
        # 0xFFFFFFFE will exclude Chinese servers from Agora's servers.
        RTC.initialize(AGORA_KEY, None, agorartc.AREA_CODE_GLOB & 0xFFFFFFFE)
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

    def __init__(self):
        self.clubhouse_audio = super().__init__()
        # Set some global variables
        # Figure this out when you're ready to start playing music

    def mute_audio(self):
        self.RTC.muteLocalAudioStream(mute=True)
        return

    def unmute_audio(self):
        self.RTC.muteLocalAudioStream(mute=False)
        return

    def start_music(self, channel, join_dict, task=None, announcement=None, interval=3600):
        # Check for the voice level.
        if self.RTC:
            token = join_dict['token']
            self.RTC.joinChannel(token, channel, "", int(self.client_id))
            self.RTC.muteLocalAudioStream(mute=False)
            Clubhouse().channel.update_audio_mode(channel)
            self.RTC.muteAllRemoteAudioStreams(mute=True)
            logging.info("RTC audio loaded")
            logging.info("RTC remote audio muted")
        else:
            logging.warning("Agora SDK is not installed.")
        return

    def terminate_music(self, channel):
        if self.RTC:
            self.RTC.leaveChannel()
        return


if __name__ == "__main__":
    pass

