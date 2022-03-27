from configparser import ConfigParser
import requests
import logging
import time

import fancy_text

from .clubhouse import Clubhouse


def read_config(section):
    """
    A function to read the config file.
    :param filename: The file to be read.
    :return config: List
    """
    config_object = ConfigParser()
    config_object.read("/Users/deon/Documents/GitHub/HQ/config.ini")

    config_object = config_object[section]

    section_list = ["Account", "S3", "RapidAPI"]
    if section in section_list:
        return dict(config_object)

    content_list = []
    for item in config_object:
        content_list.append(config_object[item])

    return content_list


class Var:
    client_id = read_config("Account")["user_id"]
    rapid_api_host = read_config("RapidAPI")["host"]
    rapid_api_key = read_config("RapidAPI")["key"]

    urban_dict_response_message_list = []
    urban_dict_response_term_list = []


class ChatClient(Clubhouse):
    pass


class UrbanDict(ChatClient):

    urban_dict_active = {}

    API_URL = "https://mashape-community-urban-dictionary.p.rapidapi.com/define"

    HEADERS = {
        "X-RapidAPI-Host": Var.rapid_api_host,
        "X-RapidAPI-Key": Var.rapid_api_key
    }

    def __init__(self, headers=None):
        """
        :arg
        """
        self.HEADERS = dict(self.HEADERS)
        if isinstance(headers, dict):
            self.HEADERS.update(headers)

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
        req = requests.get(self.API_URL, headers=self.HEADERS, params=querystring)
        logging.info(f"game_tools.UrbanDict {req}")
        definitions = req.json()['list'][0]['definition'].split('\r\n')

        if len(definitions) == 1:
            definitions = definitions[0].split(' , ')
        if len(definitions) == 1:
            definitions = definitions[0].split(' ,')

        if len(definitions) > 1:
            numbered = definitions
            definitions = []
            i = 1
            for definition in numbered:
                definition = f"{str(i)}. {definition}"
                definitions.append(definition)
                i += 1

        definition_list = []
        for definition in definitions:
            definition = definition.replace("[", "")
            definition = definition.replace("]", "")
            definition_list.append(definition)

        logging.info(f"game_tools.UrbanDict {definition_list}")

        return definition_list


def read_backchannel(client, trigger):
    backchannel = client.get_backchannel()

    if backchannel.get("success"):
        logging.info("backchannel['success']")
        chats = []
        for thread in backchannel["chats"][:5]:
            if thread["chat_type"] == "one_on_one":
                chats.append(thread)
    def search_trigger(client, chats):
        for chat in chats:
            if "urban dict" in chat["last_message"]["message_data"]["message_body"].lower():
                chat_id = chat["chat_id"]
                player_name = chat["members"][0]["name"]
                player_id = chat["members"][0]["user_profile_id"]
                UrbanDict.urban_dict_active[chat_id] = {
                    "player_name": player_name,
                    "player_id": player_id,
                }
                message = f"Hello {player_name}, what term would you like to define?"
                client.send_backchannel_message(message, chat_id)
                logging.info("ud trigger")



def urban_dict(client, channel):
    channel_message_stream = client.get_channel_messages(channel)
    logging.info(f"game_tools.urban_dict_client channel_message_stream")

    if not channel_message_stream.get("success"):
        return False

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
            user_name = user_profile.get("display_name") if user_profile.get("display_name") else user_profile.get("name")

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




























