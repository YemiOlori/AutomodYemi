# mod_settings

from configparser import ConfigParser

#Get the configparser object
config_object = ConfigParser()

#Assume we need 2 sections in the config file, let's call them USERINFO and SERVERCONFIG
config_object["USERINFO"] = {
    'client_phone_number': '',
    'client_user_id': ''
}

config_object["MODLIST1"] = {
    'name_1': 'user_id_1',
    'name_2': 'user_id_2'
}

config_object["GUESTLIST1"] = {
    'name_1': 'user_id_1',
    'name_2': 'user_id_2'
}

config_object["PINGLIST"] = {
    'name_1': 'user_id_1',
    'name_2': 'user_id_2'
}


# Write the above sections to config.ini file
def get_settings():
    with open('config.ini', 'w') as conf:
        config_object.write(conf)
        print("[.] Write settings successful")
