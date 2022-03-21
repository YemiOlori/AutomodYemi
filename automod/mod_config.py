# mod_settings

from configparser import ConfigParser

#Get the configparser object
config_object = ConfigParser()

config_object['LOGGER'] ={
    'file': 'moderation_tools.log',
    'level': 'INFO'
}

#Assume we need 2 sections in the config file, let's call them USERINFO and SERVERCONFIG
config_object["USERINFO"] = {
    'phone_number': '+16418540642',
    'user_id': '541615340'
}

config_object["SOCIALCLUBS"] = {
    'a_social_room': '135293051'
}

config_object["MODLIST1"] = {
    'Deon': '27813',
    'Disco Doggie': '2350087'
}

config_object["GUESTLIST1"] = {
    ['dsf']: {
        'A.Major': '2991260',
        'Ab': '291161',
    },
    'Alexis': '409839',
    'Ankit': '1273923840',
    'Brandon': '298207',
    'Breana': '1566581',
    'Bree': '1527064',
    'Brenna': '769545',
    'Bomani': '194113805',
    'Bonnie': '2247221',
    'Cassi': '123012',
    'Chantal': '1801861585',
    'Danyelle': '24464',
    'Deon': '27813',
    'Destiny': '628404',
    'Disco Doggie': '2350087',
    'Dezi': '1871274418',
    'Ganeesh': '107516',
    'Grace': '34496',
    'Jordan': '373271',
    'Joy': '34765',
    'JULEEN': '167752',
    'just10': '415882',
    'Kaneema': '300990',
    'LeoRising': '243603',
    'LetaShae': '1724156',
    'Mandiie': '23047',
    'Mark': '21188',
    'Marlena': '1640',
    'Mavis': '1508768079',
    'phileo': '148584',
    'Tabitha': '1414736198',
    'Taii': '4163875',
    'TRP': '47107',
    'Scotty': '12208',
    'Solar': '298894012',
}

config_object["PINGLIST"] = {
    'Deon': '27813',
    'Disco Doggie': '2350087',
    'Kaneema': '300990',
    'Tabitha': '1414736198',
    'Bonnie': '2247221',

}


# Write the above sections to config.ini file
def get_settings():
    with open('config_tesr.ini', 'w') as conf:
        config_object.write(conf)
        print("Write settings successful")
