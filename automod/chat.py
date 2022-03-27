from configparser import ConfigParser
import requests
import logging
import time

import fancy_text

from .clubhouse import Clubhouse
from .moderation import load_config
from .moderation import config_to_dict
from .moderation import set_interval


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

class UrbanDict(ChatClient):
    def __init__(self):
        """

        """
        super().__init__()
        self.URBAN_DICT_API_URL = config_to_dict(self.config_object, "UrbanDictionary", "api_url"),
        self.urban_dict_responded_message_list = []
        self.urban_dict_responded_term_list = []

    urban_dict_active = {}

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

    def urban_dict(self, channel):
        channel_message_stream = self.get_channel_messages(channel)

        # def urban_dict_trigger(channel_message_stream):

        def urban_dict_search(urban_dict_requests):
            if not urban_dict_requests:
                return False

            ud_client = UrbanDict()
            for request in urban_dict_requests:
                term = request["term"]
                defined_term = ud_client.get_definition(term)
                request["definitions"] = defined_term

            return urban_dict_requests

        def urban_dict_respond(client, channel, urban_dict_requests):
            if not urban_dict_requests:
                return False

            for request in urban_dict_requests:
                term = request["term"]
                definitions = request["definitions"]
                logging.info(f"passed: {definitions}")
                user_id = request["user_id"]
                user_profile = client.get_profile(user_id).get("user_profile")
                user_name = user_profile.get("display_name") if user_profile.get("display_name") else user_profile.get(
                    "name")

                message = f"@{user_name} From Urban Dictionary:"
                reply = client.send_channel_message(channel, message)
                logging.info(f"reply: {reply}")

                if not reply.get("success"):
                    return False

                i = 0
                for definition in definitions:
                    time.sleep(5)
                    print(i)
                    i += 1
                    reply = client.send_channel_message(channel, definition)
                    logging.info(f"reply: {reply}")
                    if not reply.get("success"):
                        return False

            return True

        urban_dict_requests = urban_dict_trigger(channel_message_stream)
        urban_dict_requests = urban_dict_search(urban_dict_requests)
        urban_dict_respond(client, channel, urban_dict_requests)

        return True










def urban_dict_main():

        def urban_dict_trigger(channel_message_stream):
            urban_dict_requests = []
            term = False
            for messages in channel_message_stream["messages"][:20]:
                message_id = messages["message_id"]
                user_id = messages["user_profile"]["user_id"]
                message = messages["message"].lower()

                if message_id in Var.urban_dict_response_message_list:
                    pass

                elif user_id == 541615340:
                    pass

                elif message.startswith("urban"):
                    message = message.split("urban dictionary: ")
                    if len(message) == 1:
                        message = message[0].split("urban dictionary ")
                    if len(message) == 1:
                        message = message[0].split("urban dict: ")
                    if len(message) == 1:
                        message = message[0].split("urban dict ")

                    term = message[1]
                    logging.info(f"game_tools.urban_dict_client.urban_dict_trigger channel message request {message}")

                elif message.startswith("ud"):
                    message = message.split("ud: ")
                    if len(message) == 1:
                        message = message[0].split("ud ")

                    term = message[1]
                    logging.info(f"game_tools.urban_dict_client.urban_dict_trigger channel message request {message}")

                if term and term not in Var.urban_dict_response_term_list:
                    request = {"message_id": message_id, "user_id": user_id, "term": term}
                    logging.info(f"game_tools.urban_dict_client.urban_dict_trigger {request}")
                    urban_dict_requests.append(request)
                    Var.urban_dict_response_message_list.append(message_id)
                    Var.urban_dict_response_term_list.append(term)

            logging.info(f"request: {urban_dict_requests}")

            return urban_dict_requests if len(urban_dict_requests) > 0 else False





















