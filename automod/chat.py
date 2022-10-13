import requests
import logging
import time
import random

from datetime import datetime

import pytz

from .clubhouse import Config
from .clubhouse import Auth
from .clubhouse import ChannelChat
from .clubhouse import Message
from .fancytext import fancy
from .clubhouse import validate_response


class ChatConfig(Auth):
    # RAPID_API_HEADERS = {
    #     "X-RapidAPI-Host": Config.config_to_dict(Config.load_config(), "RapidAPI", "host"),
    #     "X-RapidAPI-Key": Config.config_to_dict(Config.load_config(), "RapidAPI", "key")
    # }

    # URBAN_DICT_URL = Config.config_to_dict(Config.load_config(), "UrbanDictionary", "url")
    # MW_URL = Config.config_to_dict(Config.load_config(), "MW", "url")
    # MW_KEY = Config.config_to_dict(Config.load_config(), "MW", "key")
    # MW_SPANISH_KEY = Config.config_to_dict(Config.load_config(), "MW", "spanish_key")

    URBAN_DICT_URL = {}
    MW_URL = {}
    MW_KEY = {}
    MW_SPANISH_KEY = {}

    UD_PREFIXES = ("/urban", "/ud")
    MW_PREFIXES = ("/def", "/dict", "/mw")
    IMDB_PREFIXES = ("/imdb", "/IMDB")
    DICE_PREFIXES = ("/dice", "/roll", "/rolldice", "/craps")

    def __init__(self, account, config):
        """

        """
        super().__init__(account, config)
        self.chat = ChannelChat(account, config)
        self.message = Message(account, config)

        self.RAPID_API_HEADERS = {
            "X-RapidAPI-Host": Config.config_to_dict(self.load_config(), "RapidAPI", "host"),
            "X-RapidAPI-Key": Config.config_to_dict(self.load_config(), "RapidAPI", "key")
        }
        
        self.URBAN_DICT_URL = Config.config_to_dict(self.load_config(), "UrbanDictionary", "url")
        self.MW_URL = Config.config_to_dict(self.load_config(), "MW", "url")
        self.MW_KEY = Config.config_to_dict(self.load_config(), "MW", "key")
        self.MW_SPANISH_KEY = Config.config_to_dict(self.load_config(), "MW", "spanish_key")

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

    def __init__(self, account, config):
        super().__init__(account, config)
        self.urban_dict = UrbanDict(account, config)
        self.mw = MW(account, config)
        self.dice = DICE(account, config)

        self.ud_commands = []
        self.mw_commands = []
        self.imdb_commands = []
        self.dice_commands = []

    def __str__(self):
        """
        :arg
        """
        return f"ChatClient(host={self.HEADERS.get('X-RapidAPI-Host')}, key={self.HEADERS.get('X-RapidAPI-Key')})"

    def run_chat_client(self, channel, interval=120, delay=10):
        self.ud_commands = []
        self.mw_commands = []
        self.imdb_commands = []
        self.dice_commands = []

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
            logging.info(self.mw_commands)
            self.mw.run_mw_dict_client(self.mw_commands, channel, delay)

        if self.imdb_commands:
            pass
        
        if self.dice_commands:
            logging.info(self.dice_commands)
            self.dice.run_dice_client(self.dice_commands, channel, delay)

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
        dice_list = []

        logging.info(ud_list)

        for message_dict in pending_requests:
            message = message_dict.get("message").lower()

            if message.startswith(self.UD_PREFIXES):
                ud_list.append(message_dict)

            elif message.startswith(self.MW_PREFIXES):
                mw_list.append(message_dict)

            elif message.startswith(self.IMDB_PREFIXES):
                imdb_list.append(message_dict)
                
            elif message.startswith(self.DICE_PREFIXES):
                dice_list.append(message_dict)

        ud_list.reverse()
        mw_list.reverse()
        imdb_list.reverse()
        dice_list.reverse()

        logging.info(f"ud_commands: {ud_list}; "
                     f"mw_commands: {mw_list}; "
                     f"imdb_commands: {imdb_list} "
                     f"dice_commands: {dice_list}")

        self.ud_commands = ud_list
        self.mw_commands = mw_list
        self.imdb_commands = imdb_list
        self.dice_commands = dice_list

        logging.info(self.ud_commands)
        logging.info(self.mw_commands)
        logging.info(self.dice_commands)

        return

    def terminate_chat_client(self):
        """
        :return:
        """
        self.urban_dict.terminate()
        self.mw.terminate()
        return

    
class UrbanDict(ChatConfig):

    def __init__(self, account, config):
        """

        """
        self.ud_message_responded_set = set()
        self.ud_defined_term_set = set()
        super().__init__(account, config)

    def __str__(self):
        """
        :arg
        """
        return f"UrbanDict(host={self.HEADERS.get('X-RapidAPI-Host')}, key={self.HEADERS.get('X-RapidAPI-Key')})"

    def run_urban_dict_client(self, ud_requests, channel, delay=30):

        filtered_requests = self.filter_new_requests(ud_requests)
        if not filtered_requests:
            logging.info("Responses have already been sent for all ud requests")
            return

        for request in filtered_requests:
            logging.info(f"ud_requests: {request}")
            message = request.get("message")
            term = self.extract_term(message)
            logging.info(f"ud_requests: {term}")
            # undefined_term = term if term not in self.ud_defined_term_set else None
            #
            # if not undefined_term:
            #     logging.info(f"[{term}] has already been defined")
            #     continue

            defined_term = self.get_definition(term)
            definition = self.clean_definition(defined_term)

            message_id = request.get("message_id")
            user_name = request.get("user_profile").get("name")

            response = self.set_response(user_name, term, definition)
            send = self.send_command_response(channel, response, delay)

            if send:
                self.ud_defined_term_set.add(term)
                self.ud_message_responded_set.add(message_id)

    def filter_new_requests(self, ud_requests):
        filtered_requests = [_ for _ in ud_requests if _.get("message_id") not in self.ud_message_responded_set]
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
        term = message.split("/urban dict:")
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

        term = f"[Urban Dictionary] {term}"
        term = fancy.bold_serif(term)

        reply_message = f"@{user_name} {term}—{definition}"

        if len(reply_message) > 250:
            reply_message = reply_message[:250].rsplit(".", 1)[0] + "."

        logging.info(reply_message)
        return reply_message
    
    def terminate(self):
        """
        :return:
        """
        self.ud_defined_term_set = set()
        logging.info("UrbanDict client terminating")
        return


class MW(ChatConfig):

    def __init__(self, account, config):
        self.mw_message_responded_set = set()
        self.mw_defined_term_set = set()
        super().__init__(account, config)

    def __str__(self):
        pass

    def run_mw_dict_client(self, mw_requests, channel, delay=30):

        filtered_requests = self.filter_new_requests(mw_requests)
        if not filtered_requests:
            logging.info("Responses have already been sent for all mw requests")
            return

        for request in filtered_requests:
            logging.info(f"mw_requests: {request}")
            message = request.get("message")
            term = self.extract_term(message)
            logging.info(f"mw_requests: {term}")
            undefined_term = term if term not in self.mw_defined_term_set else None

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
                self.mw_defined_term_set.add(term)
                self.mw_message_responded_set.add(message_id)

    def filter_new_requests(self, mw_requests):
        filtered_requests = [_ for _ in mw_requests if _.get("message_id") not in self.mw_message_responded_set]
        return filtered_requests

    @staticmethod
    def extract_term(message):
        term = message.split("/definition: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/definition:")
        if len(term) > 1:
            return term[1]
        term = message.split("/definition ")
        if len(term) > 1:
            return term[1]
        term = message.split("/define: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/define:")
        if len(term) > 1:
            return term[1]
        term = message.split("/define ")
        if len(term) > 1:
            return term[1]
        term = message.split("/def: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/def:")
        if len(term) > 1:
            return term[1]
        term = message.split("/def ")
        if len(term) > 1:
            return term[1]
        term = message.split("/dictionary: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/dictionary:")
        if len(term) > 1:
            return term[1]
        term = message.split("/dictionary ")
        if len(term) > 1:
            return term[1]
        term = message.split("/dict: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/dict:")
        if len(term) > 1:
            return term[1]
        term = message.split("/dict ")
        if len(term) > 1:
            return term[1]
        term = message.split("/mw: ")
        if len(term) > 1:
            return term[1]
        term = message.split("/mw:")
        if len(term) > 1:
            return term[1]
        term = message.split("/mw ")
        if len(term) > 1:
            return term[1]

    def get_definition(self, term):

        @validate_response
        def api_request():

            req = requests.get(f"{self.MW_URL}{term}?key={self.MW_KEY}")
            return req

        return api_request()

    @staticmethod
    def clean_definition(definition):

        defined = "Sorry, something happened. Please try again."

        if isinstance(definition[0], dict):
            defined = [_.get("shortdef") for _ in definition][0]
            logging.info(defined)
            if defined:
                defined = defined[0]

        elif isinstance(definition, list):
            definition = definition
            word_list = ", ".join(definition[:5])
            defined = f"Sorry, I couldn't define your word. \
                      You may want to try again with one of the following: {word_list}, or {definition[6]}."
            logging.info(defined)

        logging.info(f"{defined}")

        return defined

    @staticmethod
    def set_response(user_name, term, definition):

        term = f"[Merriam-Webster] {term}"
        term = fancy.bold_serif(term)

        reply_message = f"@{user_name} {term}—{definition}"

        if len(reply_message) > 250:
            reply_message = reply_message[:250].rsplit(".", 1)[0] + "."

        logging.info(reply_message)
        return reply_message
    
    def terminate(self):
        """
        :return:
        """
        self.mw_defined_term_set = set()
        logging.info("UrbanDict client terminating")
        return
    
    
class DICE(ChatConfig):
    
    def __init__(self, account, config):
        self.dice_responded_set = set()
        super().__init__(account, config)

    def run_dice_client(self, dice_requests, channel, delay=10):
        filtered_requests = self.filter_new_requests(dice_requests)
        if not filtered_requests:
            logging.info("Responses have already been sent for all mw requests")
            return

        for request in filtered_requests:
            message_id = request.get("message_id")
            user_name = request.get("user_profile").get("name")
    
            response = self.set_response(user_name)
            send = self.send_command_response(channel, response, delay)
    
            if send:
                self.dice_responded_set.add(message_id)
    
    def filter_new_requests(self, dice_requests):
        filtered_requests = [_ for _ in dice_requests if _.get("message_id") not in self.dice_responded_set]
        return filtered_requests

    @staticmethod
    def set_response(user_name):
        roll_1 = random.randint(1, 6)
        roll_2 = random.randint(1, 6)
        
        response_1 = f"@{user_name} rolled {roll_1} and {roll_2}!"
        response_2 = f"@{user_name}, you got {roll_1} and {roll_2}!"
        response_3 = f"@{user_name}, your results are {roll_1} and {roll_2}!"
        response_4 = f"@{user_name}, here's your roll: {roll_1} and {roll_2}!"
        
        return random.choice([response_1, response_2, response_3, response_4])





