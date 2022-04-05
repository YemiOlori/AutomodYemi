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
    MW_PREFIXES = ("/def", "/dict", "/mw")
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
            logging.info(self.mw_commands)
            self.mw.run_mw_dict_client(self.mw_commands, channel, delay)

        if self.imdb_commands:
            pass

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

        logging.info(f"ud_commands: {ud_list}; mw_commands: {mw_list}; imdb_commands: {imdb_list}")

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

        filtered_requests = self.filter_new_requests(ud_requests)
        if not filtered_requests:
            logging.info("Responses have already been sent for all ud requests")
            return

        for request in filtered_requests:
            logging.info(f"ud_requests: {request}")
            message = request.get("message")
            term = self.extract_term(message)
            logging.info(f"ud_requests: {term}")
            undefined_term = term if term not in self.ud_defined_term_set else None

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

        term = f"Urban Dictionary [{term}]"
        term = fancy.bold_serif(term)

        reply_message = f"@{user_name} {term}—{definition}"

        if len(reply_message) > 250:
            reply_message = reply_message[:250].rsplit(".", 1)[0] + "."

        logging.info(reply_message)
        return reply_message

    ud_message_responded_set = set()
    ud_defined_term_set = set()


class MW(ChatConfig):

    def __init__(self):
        super().__init__()

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

        term = f"Merriam-Webster Dictionary [{term}]"
        term = fancy.bold_serif(term)

        reply_message = f"@{user_name} {term}—{definition}"

        if len(reply_message) > 250:
            reply_message = reply_message[:250].rsplit(".", 1)[0] + "."

        logging.info(reply_message)
        return reply_message

    mw_message_responded_set = set()
    mw_defined_term_set = set()


class ESPN(ChatConfig):


    def live_game(self):
        # date = result.get("eventsDate").get("day").get("date")
        events = ncaa_result.get("events")

        event_0 = events[0]
        event_0_status = event_0.get("status").get("type").get("detail")
        event_0_name = event_0.get("name")
        event_0_short_name = event_0.get("shortName")
        # event_0_line =  event_0.get("competitions")[0].get("odds")[0].get("details")
        # event_0_over_under = event_0.get("competitions")[0].get("odds")[0].get("overUnder")

        team_0 = event_0.get("competitions")[0].get("competitors")[0]
        team_0_home_away = team_0.get("homeAway")
        team_0_display_name = team_0.get("team").get("displayName")
        team_0_short_display_name = team_0.get("team").get("shortDisplayName")
        team_0_abbr = team_0.get("team").get("abbreviation")
        team_0_score = team_0.get("score")

        team_0_season_stats = team_0.get("statistics")
        stat_avgs = [stat for stat in team_0_season_stats if stat.get("name").startswith("avg")]
        stat_pct = [stat for stat in team_0_season_stats if stat.get("name").endswith("Pct")]
        team_0_season_avgs = stat_avgs + stat_pct

        team_0_avgs = []
        for stat in team_0_season_avgs:
            stat_cat = stat.get("abbreviation")
            stat_value = stat.get("displayValue")
            stat_rank = stat.get("rankDisplayValue")

            stat_line = f"{stat_cat}: {stat_value} [{stat_rank}]"
            team_0_avgs.append(stat_line)

        team_0_stat_line = ", ".join(team_0_avgs)

        team_1 = event_0.get("competitions")[0].get("competitors")[1]
        team_1_home_away = team_1.get("homeAway")
        team_1_display_name = team_1.get("team").get("displayName")
        team_1_short_display_name = team_1.get("team").get("shortDisplayName")
        team_1_abbr = team_1.get("team").get("abbreviation")
        team_1_score = team_1.get("score")

        team_1_season_stats = team_1.get("statistics")
        stat_avgs = [stat for stat in team_1_season_stats if stat.get("name").startswith("avg")]
        stat_pct = [stat for stat in team_1_season_stats if stat.get("name").endswith("Pct")]
        team_1_season_avgs = stat_avgs + stat_pct

        team_1_avgs = []
        for stat in team_1_season_avgs:
            stat_cat = stat.get("abbreviation")
            stat_value = stat.get("displayValue")
            stat_rank = stat.get("rankDisplayValue")

            stat_line = f"{stat_cat}: {stat_value} [{stat_rank}]"
            team_1_avgs.append(stat_line)

        team_1_stat_line = ", ".join(team_1_avgs)

        if team_0_home_away == "home":
            response = f"{team_1_abbr} {team_1_score} | {team_0_abbr} {team_0_score} | {event_0_status}"

        else:
            response = f"{team_0_abbr} {team_0_score} | {team_1_abbr} {team_1_score} | {event_0_status}"

        return response

    def pre_game(self):

        # date = result.get("eventsDate").get("day").get("date")
        events = nba_result.get("events")

        event_0 = events[0]
        event_0_date = event_0.get("status").get("type").get("detail")
        event_0_name = event_0.get("name")
        event_0_short_name = event_0.get("shortName")
        event_0_line = event_0.get("competitions")[0].get("odds")[0].get("details")
        event_0_over_under = event_0.get("competitions")[0].get("odds")[0].get("overUnder")

        team_0 = event_0.get("competitions")[0].get("competitors")[0]
        team_0_home_away = team_0.get("homeAway")
        team_0_display_name = team_0.get("team").get("displayName")
        team_0_short_display_name = team_0.get("team").get("shortDisplayName")
        team_0_abbr = team_0.get("team").get("abbreviation")
        team_0_record = team_0.get("records")[0].get("summary")

        team_0_season_stats = team_0.get("statistics")
        stat_avgs = [stat for stat in team_0_season_stats if stat.get("name").startswith("avg")]
        stat_pct = [stat for stat in team_0_season_stats if stat.get("name").endswith("Pct")]
        team_0_season_avgs = stat_avgs + stat_pct

        team_0_avgs = []
        for stat in team_0_season_avgs:
            stat_cat = stat.get("abbreviation")
            stat_value = stat.get("displayValue")
            stat_rank = stat.get("rankDisplayValue")

            stat_line = f"{stat_cat}: {stat_value} [{stat_rank}]"
            team_0_avgs.append(stat_line)

        team_0_stat_line = ", ".join(team_0_avgs)

        team_1 = event_0.get("competitions")[0].get("competitors")[1]
        team_1_home_away = team_1.get("homeAway")
        team_1_display_name = team_1.get("team").get("displayName")
        team_1_short_display_name = team_1.get("team").get("shortDisplayName")
        team_1_abbr = team_1.get("team").get("abbreviation")
        team_1_record = team_1.get("records")[0].get("summary")

        team_1_season_stats = team_1.get("statistics")
        stat_avgs = [stat for stat in team_1_season_stats if stat.get("name").startswith("avg")]
        stat_pct = [stat for stat in team_1_season_stats if stat.get("name").endswith("Pct")]
        team_1_season_avgs = stat_avgs + stat_pct

        team_1_avgs = []
        for stat in team_1_season_avgs:
            stat_cat = stat.get("abbreviation")
            stat_value = stat.get("displayValue")
            stat_rank = stat.get("rankDisplayValue")

            stat_line = f"{stat_cat}: {stat_value} [{stat_rank}]"
            team_1_avgs.append(stat_line)

        team_1_stat_line = ", ".join(team_1_avgs)

        if team_0_home_away == "home":
            response = f"{team_1_display_name} [{team_1_record}] @ {team_0_display_name} [{team_0_record}] | \
                       {event_0_date} | {event_0_line} | O/U {event_0_over_under}"

        else:
            response = f"{team_0_display_name} [{team_0_record}] @ {team_1_display_name} [{team_1_record}] |  \
                       {event_0_date} | {event_0_line} | O/U {event_0_over_under}"

        return response







