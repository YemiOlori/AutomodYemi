from configparser import ConfigParser
import requests
from .clubhouse_api import Clubhouse
from .moderation_tools import set_interval

set_interval =

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



client_id = read_config("Account")["user_id"]
rapid_api_host = read_config("RapidAPI")["host"]
rapid_api_key = read_config("RapidAPI")["key"]

class UrbanDict():

    urban_dict_active = []

    API_URL = "https://mashape-community-urban-dictionary.p.rapidapi.com/define"

    HEADERS = {
        "X-RapidAPI-Host": rapid_api_host,
        "X-RapidAPI-Key": rapid_api_key
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
        definition = req.json()['list'][0]['definition'].split('\r\n')

        return definition




@set_interval(30)
def urban_dict_client(client):

    def search_trigger:
        backchannel = client.get_backchannel()
        if backchannel["success"]:
            chats = backchannel["chats"][:5]
            for chat in chats:
                if "urban dict" in chat["last_message"]["message_data"]["message_body"].lower():
                    chat_id = chat["chat_id"]
                    player_name = chat["name"]
                    player_id = chat["user_profile_id"]
                    UrbanDict.urban_dict_active.append({
                        "chat_id": chat_id,
                        "player_name": player_name,
                        "player_id": player_id,
                    })
                    message = f"Hello {player_name}, what term would you like to define?"
                    client.send_backchannel_message(message, chat_id=chat_id)

    def 





















