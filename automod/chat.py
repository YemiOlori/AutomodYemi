import requests
import logging
import time
from datetime import datetime

import pytz

from .clubhouse import Config
from .clubhouse import Auth
from .clubhouse import ChannelChat
from .clubhouse import Message
from .fancytext import fancy
from .clubhouse import validate_response


class ChatConfig(Auth):
    RAPID_API_HEADERS = {
        "X-RapidAPI-Host": Config.config_to_dict(Config.load_config(), "RapidAPI", "host"),
        "X-RapidAPI-Key": Config.config_to_dict(Config.load_config(), "RapidAPI", "key")
    }

    URBAN_DICT_URL = Config.config_to_dict(Config.load_config(), "UrbanDictionary", "url")

    MW_URL = Config.config_to_dict(Config.load_config(), "MW", "url")
    MW_KEY = Config.config_to_dict(Config.load_config(), "MW", "key")
    MW_SPANISH_KEY = Config.config_to_dict(Config.load_config(), "MW", "spanish_key")

    UD_PREFIXES = ("/urban", "/ud")
    MW_PREFIXES = ("/def", "/dict")
    IMDB_PREFIXES = ("/imdb", "/IMDB")

    def __init__(self):
        """

        """
        super().__init__()
        self.chat = ChannelChat()
        self.message = Message()

    def send_command_response(self, channel, message, delay=10):
        response = False

        if isinstance(message, str):
            message = [message]

        for _ in message:
            run = self.chat.send_chat(channel, _)
            response = run.get("success")
            time.sleep(delay)

        return response


class ChatClient(ChatConfig):

    def __init__(self):
        super().__init__()
        self.urban_dict = UrbanDict()
        self.mw = MW()

    def __str__(self):
        """
        :arg
        """
        return f"ChatClient(host={self.HEADERS.get('X-RapidAPI-Host')}, key={self.HEADERS.get('X-RapidAPI-Key')})"

    def run_chat_client(self, channel, interval=120, delay=10):
        self.ud_commands = []
        self.mw_commands = []
        self.imdb_commands = []


        chat_stream = self.get_chat_stream(channel)
        if not chat_stream:
            return

        chat_messages_list = self.check_for_messages(chat_stream)
        if not chat_messages_list:
            return

        requests_list = self.check_for_command(chat_messages_list)
        if not requests_list:
            return

        recent_requests_list = self.recent_requests_filter(requests_list, interval)
        if not recent_requests_list:
            return

        self.filter_commands(recent_requests_list)

        if self.ud_commands:
            logging.info(self.ud_commands)
            self.urban_dict.run_urban_dict_client(self.ud_commands, channel, delay)

        if self.mw_commands:
            pass

        if self.imdb_commands:
            pass

        mw_client = []
        imdb_client = []

        return True

    def get_chat_stream(self, channel):
        chat_stream = self.chat.get_chat(channel)
        return chat_stream

    @staticmethod
    def check_for_messages(chat_stream):
        messages = chat_stream.get("messages")

        if not messages:
            logging.info("No messages in chat stream")

        return messages

    @staticmethod
    def check_for_command(chat_messages_list):

        chat_command_list = []
        for message_dict in chat_messages_list:
            message = message_dict.get("message")

            if message.startswith("/"):
                chat_command_list.append(message_dict)

        if not chat_command_list:
            logging.info("No chat commands found")

        return chat_command_list

    @staticmethod
    def recent_requests_filter(requests_list, interval):

        recent_commands_list = []
        for message_dict in requests_list:

            time_created = message_dict.get("time_created")
            time_created = datetime.strptime(time_created, '%Y-%m-%dT%H:%M:%S.%f%z')
            time_now = datetime.now(pytz.timezone('UTC'))
            time_diff = time_now - time_created
            time_diff = time_diff.total_seconds()

            if time_diff <= interval:
                recent_commands_list.append(message_dict)

        if not recent_commands_list:
            logging.info("No recent requests in chat stream")

        return recent_commands_list

    def filter_commands(self, pending_requests):

        ud_list = []
        mw_list = []
        imdb_list = []

        logging.info(ud_list)

        for message_dict in pending_requests:
            message = message_dict.get("message").lower()

            if message.startswith(self.UD_PREFIXES):
                ud_list.append(message_dict)

            elif message.startswith(self.MW_PREFIXES):
                mw_list.append(message_dict)

            elif message.startswith(self.IMDB_PREFIXES):
                imdb_list.append(message_dict)

        ud_list.reverse()
        mw_list.reverse()
        imdb_list.reverse()

        logging.info(ud_list)

        self.ud_commands = ud_list
        self.mw_commands = mw_list
        self.imdb_commands = imdb_list

        logging.info(self.ud_commands)

        return

    ud_commands = []
    mw_commands = []
    imdb_commands = []


class UrbanDict(ChatConfig):

    def __init__(self):
        """

        """
        super().__init__()

    def __str__(self):
        """
        :arg
        """
        return f"UrbanDict(host={self.HEADERS.get('X-RapidAPI-Host')}, key={self.HEADERS.get('X-RapidAPI-Key')})"

    def run_urban_dict_client(self, ud_requests, channel, delay=30):

        logging.info(f"ud_requests: {ud_requests}")
        filtered_requests = self.filter_new_requests(ud_requests)
        if not filtered_requests:
            logging.info("All responses have already been sent for all requests")
            return

        for request in filtered_requests:
            logging.info(f"ud_requests: {request}")
            message = request.get("message")
            term = self.extract_term(message)
            logging.info(f"ud_requests: {term}")
            undefined_term = term if term not in self.defined_term_set else None

            if not undefined_term:
                logging.info(f"[{term}] has already been defined")
                continue

            defined_term = self.get_definition(term)
            definition = self.clean_definition(defined_term)

            message_id = request.get("message_id")
            user_name = request.get("user_profile").get("name")

            response = self.set_response(user_name, term, definition)
            send = self.send_command_response(channel, response, delay)

            if send:
                self.message_responded_set.add(term)
                self.message_responded_set.add(message_id)

    def filter_new_requests(self, ud_requests):
        filtered_requests = [_ for _ in ud_requests if _.get("message_id") not in self.message_responded_set]
        return filtered_requests

    @staticmethod
    def extract_term(message):
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

    def get_definition(self, term):
        """
        :param term:
        :return:
        """
        @validate_response
        def api_request():
            querystring = {
                "term": term
            }
            req = requests.get(self.URBAN_DICT_URL, headers=self.RAPID_API_HEADERS, params=querystring)
            return req

        response = api_request()
        if not response.get("list"):
            return f'No definition for "{term}" was found on Urban Dictionary'

        definition = response.get("list")[0]["definition"]
        return definition

    @staticmethod
    def clean_definition(definition):

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

    @staticmethod
    def set_response(user_name, term, definition):

        term = f"Urban Dictionary [lookup: {term}]"
        term = fancy.bold_serif(term)

        reply_message = f"@{user_name} {term}—{definition}"
        reply_message = reply_message[:300]
        logging.info(reply_message)

        return reply_message

    message_responded_set = set()
    defined_term_set = set()


class MW(ChatConfig):

    def __init__(self):
        super().__init__()

    def __str__(self):
        pass

    def get_definition(self, term):

        @validate_response
        def api_request():

            req = requests.get(f"{self.MW_URL}{term}?key={self.MW_KEY}")
            return req

        return api_request()







