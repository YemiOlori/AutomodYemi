import requests
import logging
import time
from datetime import datetime

import pytz

from .clubhouse import Config
from .clubhouse import Auth
from .clubhouse import ChannelChat
from .clubhouse import Message
from .clubhouse import User
from .fancytext import fancy


class ChatConfig(Auth):
    RAPID_API_HEADERS = {
        "X-RapidAPI-Host": Config.config_to_dict(Config.load_config(), "RapidAPI", "host"),
        "X-RapidAPI-Key": Config.config_to_dict(Config.load_config(), "RapidAPI", "key")
    }

    URBAN_DICT_API_URL = Config.config_to_dict(Config.load_config(), "UrbanDictionary", "api_url")

    UD_PREFIXES = ("/urban", "/ud")
    MW_PREFIXES = ("/def", "/dict")
    IMDB_PREFIXES = ("/imdb")



class ChatClient(ChatConfig):

    command_responded_list = []

    def __init__(self):
        """

        """
        super().__init__()
        self.UrbanDict = UrbanDict()
        self.chat = ChannelChat()
        self.message = Message()

    def __str__(self):
        """
        :arg
        """
        return f"ChatClient(host={self.HEADERS.get('X-RapidAPI-Host')}, key={self.HEADERS.get('X-RapidAPI-Key')})"

    def check_chat_stream(self, channel, chat_stream=None):
        if channel and not chat_stream:
            chat_stream = self.chat.get_chat(channel)
        return chat_stream

    @staticmethod
    def check_for_messages(chat_stream):
        if not isinstance(chat_stream, dict):
            logging.info("No response from server")
            return

        elif not chat_stream.get("success"):
            logging.info("Chat stream not pulled")
            return

        elif chat_stream.get("messages"):
            return chat_stream.get("messages")
        else:
            logging.info("No messages in chat stream")

    @staticmethod
    def check_for_triggers(message_list):
        if not message_list:
            return

        command_triggered_list = []
        for message in message_list:
            if message.get("message").startswith("/"):
                logging.info(message)
                command_triggered_list.append(message)

        if command_triggered_list:
            return command_triggered_list
        else:
            logging.info("No command triggers found")

    @staticmethod
    def check_time_diff(command_triggered_list, interval):
        if not command_triggered_list:
            return

        recent_commands_list = []
        for message in command_triggered_list:

            time_created = message.get("time_created")
            time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
            time_now = datetime.now(pytz.timezone('UTC'))
            time_diff = time_now - time_created
            time_diff = time_diff.total_seconds()

            if time_diff <= interval:
                recent_commands_list.append(message)

        if recent_commands_list:
            return recent_commands_list
        else:
            logging.info("No recent requests in chat stream")

    def check_response_status(self, recent_requests):
        if not recent_requests:
            return

        pending_requests_list = []
        for message in recent_requests:
            if not message.get("message_id") in self.command_responded_list:
                pending_requests_list.append(message)
                logging.info(f"Room chat command received: {message.get('message')}")

        if len(pending_requests_list) > 0:
            return pending_requests_list
        else:
            logging.info("No new requests in chat stream")

    def filter_commands(self, pending_requests):
        if not pending_requests:
            return

        ud_list = []
        mw_list = []
        imdb_list = []
        for message in pending_requests:
            command = message.get("message").lower()
            if command.startswith(self.UD_PREFIXES):
                ud_list.append(message)

            elif command.startswith(self.MW_PREFIXES):
                mw_list.append(message)

            elif command.startswith(self.IMDB_PREFIXES):
                imdb_list.append(message)

        ud_list.reverse()
        mw_list.reverse()
        imdb_list.reverse()

        command_triggered_dict = {
            "urban_dict": ud_list,
            "mw_dict": mw_list,
            "imdb": imdb_list,
        }

        logging.info(command_triggered_dict)
        return command_triggered_dict

    def respond_to_request(self, channel, response_list):
        if not response_list:
            return

        for response in response_list:
            self.chat.send_chat(channel, response)
            time.sleep(10)

    def run_chat_client(self, channel, interval=30, chat_stream=None):

        chat_stream = self.check_chat_stream(channel, chat_stream)
        message_list = self.check_for_messages(chat_stream)
        triggered_list = self.check_for_triggers(message_list)
        recent_requests_list = self.check_time_diff(triggered_list, interval)
        new_requests = self.check_response_status(recent_requests_list)
        filtered_requests_dict = self.filter_commands(new_requests)

        if not filtered_requests_dict:
            return

        ud_client = self.UrbanDict.run_urban_dict_client(filtered_requests_dict)
        mw_client = []
        imdb_client = []

        chat_response_list = ud_client + mw_client + imdb_client

        self.respond_to_request(channel, chat_response_list)


class UrbanDict(ChatConfig):
    ud_term_defined_list = []

    def __init__(self):
        """

        """
        super().__init__()
        self.user = User()

    def __str__(self):
        """
        :arg
        """
        return f"UrbanDict(host={self.HEADERS.get('X-RapidAPI-Host')}, key={self.HEADERS.get('X-RapidAPI-Key')})"

    @staticmethod
    def check_for_ud_command(requests_dict):
        if not requests_dict.get("urban_dict"):
            logging.info("No new urban dict requests in chat stream")
            return
        requests_list = requests_dict.get("urban_dict")
        return requests_list

    @staticmethod
    def _extract_term(message):
        term = message.split("/urban dictionary: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/urban dictionary:")
        if len(term) > 1:
            return term[1]
        term = message.split("/urban dictionary ")
        if len(term) > 1:
            return term[1]
        term = message.split("/urban dict: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/urban dict ")
        if len(term) > 1:
            return term[1]
        term = message.split("/ud: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/ud:")
        if len(term) > 1:
            return term[1]
        term = message.split("/ud ")
        if len(term) > 1:
            return term[1]

    @staticmethod
    def _append_term_to_request(request, term):
        request["term"] = term
        return request

    def _filter_defined_terms(self, term):
        if term not in self.ud_term_defined_list:
            return term
        else:
            logging.info("Term has already been defined")

    def _update_request_list(self, request_list):
        updated_request_list = []
        for request in request_list:
            message = request.get("message")
            term = self._extract_term(message)
            term = self._filter_defined_terms(term)

            if term:
                updated_request = self._append_term_to_request(request, term)
                updated_request_list.append(updated_request)

        if updated_request_list:
            return updated_request_list
        else:
            logging.info("All terms have already been defined")

    def get_definition(self, term):
        """
        :param term:
        :return:
        """
        querystring = {
            "term": term
        }
        req = requests.get(self.URBAN_DICT_API_URL, headers=self.RAPID_API_HEADERS, params=querystring)
        logging.info(f"{req.status_code} {req.text}")
        if not req:
            return False
        elif not req.json().get("list"):
            return f"No definition for {term} was found on Urban Dictionary"

        definition = req.json().get("list")[0]["definition"]
        return definition

    @staticmethod
    def clean_definition(definition):
        if not definition:
            return

        multi_line_list = []
        definition = definition.splitlines()
        for line in definition:
            line = line.replace("[", "")
            line = line.replace("]", "")
            line = line.replace(" ,", ", ")
            line = line.strip(" ")
            multi_line_list.append(line)

        definition = " ".join(multi_line_list)
        logging.info(f"{definition}")

        return definition

    def config_response_dict(self, pending_requests):
        if not pending_requests:
            return

        pending_responses_list = []
        for request in pending_requests:
            message_id = request.get("message_id")
            user_id = request.get("user_profile").get("user_id")
            user_name = request.get("user_profile").get("name")
            term = request.get("term")
            defined_term = self.get_definition(term)
            definition = self.clean_definition(defined_term)
            request_response_dict = {
                "message_id": message_id,
                "user_id": user_id,
                "user_name": user_name,
                "term": term,
                "definition": definition,
            }

            logging.info(request_response_dict)
            pending_responses_list.append(request_response_dict)
        return pending_responses_list

    def response_message_list(self, response_dict):

        response_list = []
        for response in response_dict:
            user_name = response.get("user_name")
            term = response.get("term")
            definition = response.get("definition")

            term = f"Urban Dictionary [lookup: {term}]"
            term = fancy.bold_serif(term)

            reply_message = f"@{user_name} {term}—{definition}"
            print(reply_message)
            response_list.append(reply_message)
            logging.info(reply_message)
            self.ud_term_defined_list.append(term)

        return response_list

    def run_urban_dict_client(self, requests_dict):
        ud_request_list = self.check_for_ud_command(requests_dict)
        if not ud_request_list:
            return []

        updated_request_list = self._update_request_list(ud_request_list)
        pending_response_dict = self.config_response_dict(updated_request_list)
        response_list = self.response_message_list(pending_response_dict)

        return response_list




