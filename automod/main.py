#!/usr/bin/env python

import sys
import logging
from configparser import ConfigParser

from .clubhouse import Clubhouse


def set_logging_config():

    def read_config_dict(section):
        """
        A function to read the config file.
        :param section: The section to be read.
        :return config: Dict or List
        """
        config_file = "/Users/deon/Documents/GitHub/HQ/config.ini"
        config_object = ConfigParser()
        config_object.read(config_file)

        if section not in config_object.sections():
            raise Exception(f"Error in fetching config in read_config method. {section} not found in config file.")

        config_section = dict(config_object[section])

        return config_section

    logging_config = read_config_dict("Logging")

    folder = logging_config.get("folder")
    file = logging_config.get("file")
    level = logging_config.get("level")
    filemode = logging_config.get("filemode")
    logging.basicConfig(
        filename=f"{folder}{file}",
        filemode=filemode,
        format="%(asctime)s - %(module)s - %(levelname)s - line %(lineno)d - "
               "%(funcName)s - %(message)s (Process Details: (%(process)d, "
               "%(processName)s) Thread Details: (%(thread)d, %(threadName)s))",
        datefmt="%Y-%d-%m %I:%M:%S",
        level=level)


def main():
    pass

















if __name__ == '__main__':
    set_logging_config()
    main()