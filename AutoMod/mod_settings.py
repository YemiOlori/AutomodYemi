# mod_settings

from configparser import ConfigParser

#Get the configparser object
config_object = ConfigParser()

#Assume we need 2 sections in the config file, let's call them USERINFO and SERVERCONFIG
config_object["USERINFO"] = {
    'phone_number': '+16418540642',
    'user_id': '541615340'
}

config_object["GUESTLIST1"] = {
    'Ankit': '1273923840',
    'Breana': '1566581',
    'Disco Doggie': '2350087',
    'Dezi': '1871274418',
    'Grace': '34496',
    'Jordan': '373271',
    'Mark': '21188',
    'Marlena': '1640',
    'Tabitha': '1414736198',
    'Taii': '4163875',
    'TRP': '47107',
    'Scotty': '12208',
    'Solar': '298894012'
}

#Write the above sections to config.ini file
with open('config.ini', 'w') as conf:
    config_object.write(conf)
    print("Write successful")
