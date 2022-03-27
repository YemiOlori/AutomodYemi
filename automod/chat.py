from configparser import ConfigParser
import requests
import logging
import time
from datetime import datetime

import fancy_text
import pytz

from .clubhouse import Clubhouse
from .moderation import load_config
from .moderation import config_to_dict

class ChatClient(Clubhouse):
    def __init__(self):
        """

        """
        super().__init__()
        self.client_id = self.HEADERS.get('CH-UserID')

        config_file = "/Users/deon/Documents/GitHub/HQ/config.ini"
        self.config_object = load_config(config_file)
        self.RAPID_API_HEADERS = {
            "X-RapidAPI-Host": config_to_dict(self.config_object, "RapidAPI", "host"),
            "X-RapidAPI-Key": config_to_dict(self.config_object, "RapidAPI", "key")
        }
        self.command_responded_list = []

    def get_channel_stream(self, channel):
        channel_message_stream = self.get_channel_messages(channel)

        command_triggered_list = []
        for messages in channel_message_stream.get("messages")[:20]:
            message_id = messages.get("message_id")
            time_diff = None

            if message.startswith("/"):
                time_created = message.get("time_created")
                time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
                time_now = datetime.now(pytz.timezone('UTC'))
                time_diff = time_now - time_created
                time_diff = time_diff.total_seconds()

            if  time_diff <= 30 and message_id not in self.command_responded_list:
                command_triggered_list.append(messages)
                logging.info(f"Channel message command {message}")

        return command_triggered_list

    def check_command(self, channel):
        command_triggered_list = self.get_channel_stream(channel)
        ud_prefixes = ["/urban", "/ud"]
        mw_prefixes = ["/def", "/dict"]
        imdb_prefixes = ["/imdb"]

        urban_dict_list = []
        mw_dict_list = []
        imdb_list = []
        for messages in command_triggered_list:
            message = messages("message").lower()

            if message.startswith(tuple(ud_prefixes)):
                urban_dict_list.append(messages)
            elif message.startswith(tuple(mw_prefixes)):
                mw_dict_list.append(messages)
            elif message.startswith(tuple(imdb_prefixes)):
                imdb_list.append(messages)

        triggered = {
            "urban_dict": urban_dict_list,
            "mw_dict": mw_dict_list,
            "imdb": imdb_list,
        }
        return triggered


class UrbanDict(ChatClient):
    def __init__(self):
        """

        """
        super().__init__()
        self.URBAN_DICT_API_URL = config_to_dict(self.config_object, "UrbanDictionary", "api_url")
        self.ud_thread = None
        self.ud_defined_list = []

    # urban_dict_active = {}

    def __str__(self):
        """
        :arg
        """
        return f"UrbanDict(host={self.HEADERS.get('X-RapidAPI-Host')}, key={self.HEADERS.get('X-RapidAPI-Key')})"

    def get_definition(self, term):
        """
        :param term:
        :return:
        """
        querystring = {
            "term": term
        }
        req = requests.get(self.URBAN_DICT_API_URL, headers=self.RAPID_API_HEADERS, params=querystring)
        logging.info(f"{req}")
        definitions = req.json()['list'][0]['definition'].split('\r\n')

        # if len(definitions) == 1:
        #     definitions = definitions[0].split(' , ')
        # if len(definitions) == 1:
        #     definitions = definitions[0].split(' ,')
        #
        # if len(definitions) > 1:
        #     numbered = definitions
        #     definitions = []
        #     i = 1
        #     for definition in numbered:
        #         definition = f"{str(i)}. {definition}"
        #         definitions.append(definition)
        #         i += 1

        definition_list = []
        for definition in definitions:
            definition = definition.replace("[", "")
            definition = definition.replace("]", "")
            definition_list.append(definition)

        logging.info(f"{definition_list}")

        return definition_list

    def urban_dict_trigger(self, message_list):
        urban_dict_requests = []
        for messages in message_list:
            message_id = messages.get("message_id")
            user_id = messages.get("user_id")
            message = messages("message").lower()

            if message.startswith("/urban"):
                message = message.split("/urban dictionary: ")
                if len(message) == 1:
                    message = message[0].split("/urban dictionary ")
                if len(message) == 1:
                    message = message[0].split("/urban dict: ")
                if len(message) == 1:
                    message = message[0].split("/urban dict ")

            elif message.startswith("/ud"):
                message = message.split("/ud: ")
                if len(message) == 1:
                    message = message[0].split("/ud ")

            term = message[1]
            if term and term not in self.ud_defined_list:
                request = {"message_id": message_id, "user_id": user_id, "term": term}
                logging.info(f"Urban Dict command {request}")
                urban_dict_requests.append(request)

        return urban_dict_requests if len(urban_dict_requests) > 0 else False

    def urban_dict(self, channel, message_list):
        urban_dict_requests = self.urban_dict_trigger(message_list)
        if not urban_dict_requests:
            return False

        for request in urban_dict_requests:
            term = request.get("term")
            definition= self.get_definition(term)

            user_id = request.get("user_id")
            user_profile = self.get_profile(user_id).get("user_profile")
            user_name = (
                user_profile.get("display_name") if user_profile.get("display_name")
                else user_profile.get("name")
            )

            reply_message = f"@{user_name}: 𝗨𝗿𝗯𝗮𝗻 𝗗𝗶𝗰𝘁𝗶𝗼𝗻𝗮𝘆 [{term}]: {definition}"
            self.send_channel_message(channel, reply_message)
            self.command_responded_list.append(request.get("message_id"))
            self.ud_defined_list.append(term)

        return True



def chat_client(channel):
    _chat_client = ChatClient()
    ud_client = UrbanDict()

    message_list = _chat_client.check_command(channel)

    if message_list.get("urban_dict"):
        ud_client.urban_dict(channel, message_list.get("urban_dict"))






















