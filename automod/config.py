# mod_settings

from configparser import ConfigParser

# Get the configparser object
config_object = ConfigParser()

config_object["ClientInfo"] = {
    'client_phone_number': '',
    'client_user_id': ''
}

config_object["ModList"] = {
    'name_1': 'user_id_1',
    'name_2': 'user_id_2'
}

config_object["GuestList"] = {
    'name_1': 'user_id_1',
    'name_2': 'user_id_2'
}

config_object["PingList"] = {
    'name_1': 'user_id_1',
    'name_2': 'user_id_2'
}


# Write the above sections to config.ini file
def get_settings():
    with open('config.ini', 'w') as conf:
        config_object.write(conf)
        print("[.] Write settings successful")
