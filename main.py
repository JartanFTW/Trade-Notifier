import requests #Using requests so people don't have to install extra modules.
import json
from configparser import ConfigParser
import logging
import os
import time

clear = lambda: os.system("cls")

def setup_logging(level=40):

    path = os.path.dirname(os.path.abspath(__file__))

    logs_folder_path = os.path.join(path, "logs")

    if not os.path.exists(logs_folder_path):
        os.makedirs(logs_folder_path)
    
    log_path = os.path.join(logs_folder_path, time.strftime('%m %d %Y %H %M %S', time.localtime()))

    logging.basicConfig(filename=f"{log_path}.log", level=level, format="%(asctime)s:%(levelname)s:%(message)s")



def load_config():
    parser = ConfigParser()

    parser.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "notifier_config.ini"))

    config = {}

    config["webhook"] = str(parser["GENERAL"]["webhook"]).strip()
    config["cookie"] = ".ROBLOSECURITY=_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_" + str(parser["GENERAL"]["cookie"]).split("_")[-1]
    config["logging_level"] = int(parser["DEBUG"]["logging_level"])
    return config


def main():
    config = load_config()
    setup_logging(config["logging_level"])
    pass

if __name__ == "__main__":
    main()