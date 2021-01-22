#  Copyright 2021 Jonathan Carter

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.



import logging
import time
import httpx
import sys
import asyncio
from PIL import Image
from io import BytesIO
import os
from configparser import ConfigParser

logger = logging.getLogger("horizon.utilities")



class UnknownResponse(Exception):

    def __init__(self, response_code: int, request_url: str, response_text: str = None):

            self.response_code = response_code

            self.request_url = request_url

            self.response_text = response_text

            self.err = f"Unknown response code {response_code} was received."

            logger.critical(f"An unknown response {response_code} was received when calling {request_url}")

            super().__init__(self.err)



class InvalidCookie(Exception):

    def __init__(self, response_code: int, request_url: str, response_text: str = None):

        self.response_code = response_code

        self.request_url = request_url

        self.response_text = response_text

        self.err = f"Input cookie is invalid and returned response code {response_code}."

        logger.critical(f"An invalid cookie was detected with response code {response_code} when calling {request_url}")

        super().__init__(self.err)



def print_timestamp(text: str):
    print(time.strftime('%H:%M:%S | ', time.localtime()) + text)



async def get_asset_image_url( item_ids: list, format: str = "Png", isCircular: str = "false", size: str = "110x110"):

    async with httpx.AsyncClient() as client:
        
        while True:

            logger.info("Grabbing asset image urls")

            request = await client.get(f"https://thumbnails.roblox.com/v1/assets?assetIds={',+'.join(item_ids)}&format={format}&isCircular={isCircular}&size={size}")

            if request.status_code == 200:

                request_json = request.json()

                logger.debug(f"Grabbed asset image urls: {request_json}")

                return request_json

            logger.warning(f"Failed to grab asset image urls: {request.status_code}")

            if request.status_code == 429:

                await asyncio.sleep(5)

                continue

            else:

                logger.critical(f"Encountered an unhandled response code while updating user csrf: {request.status_code}")

                raise UnknownResponse(request.status_code, request.url, response_text = request.text)



async def get_pillow_object_from_url(url: str):

    async with httpx.AsyncClient() as client:

        while True:

            logger.info(f"Creating pillow Image object from url: {url}")

            request = await client.get(url)

            if request.status_code == 200:
                
                p_obj = Image.open(request)

                logger.debug(f"Created pillow Image object from url: {url}")

                return p_obj
            
            logger.warning(f"Failed to create pillow Image object from url: {request.status_code}")

            if request.status_code == 429:

                await asyncio.sleep(5)

                continue

            else:

                logger.critical(f"Encountered an unknown response code while creating pillow Image object from url: {request.status_code}")

                raise UnknownResponse(request.status_code, request.url, response_text = request.text)



async def send_trade_webhook(webhook_url: str, attachments: list = None): # TODO Rewrite properly utilizing **kwargs for custom request stuffs.

    files = {}
    for i in range(len(attachments)):
        files[f"file_{i}"] = (attachments[i][0], attachments[i][1])

    async with httpx.AsyncClient() as client:

        logger.info("Sending trade webhook")

        request = await client.post(webhook_url, files = files)
    
    if request.status_code == 200:

        logger.debug("Sent trade webhook")

        return

    else:

        logger.error("Failed to send trade webhook")

        raise UnknownResponse(request.status_code, request.url, response_text = request.text)



async def get_roli_values():

    async with httpx.AsyncClient() as client:

        logger.info("Getting rolimon's values")

        request = await client.get("https://www.rolimons.com/itemapi/itemdetails")

    if request.status_code == 200:

        request_json = request.json()

        logger.debug(f"Got rolimon's values: {request_json}")

        return request_json
    
    else:

        logger.critical(f"Failed to update rolimons values: {request.status_code}")

        raise UnknownResponse(request.status_code, request.url, response_text = request.text)



def setup_logging(path: str, level=40):

    logs_folder_path = os.path.join(path, "logs")

    if not os.path.exists(logs_folder_path):
        os.makedirs(logs_folder_path)
    
    log_path = os.path.join(logs_folder_path, time.strftime('%m %d %Y %H %M %S', time.localtime()))

    logging.basicConfig(filename=f"{log_path}.log", level=level, format="%(asctime)s:%(levelname)s:%(message)s")



def load_config(path: str):

    parser = ConfigParser()

    parser.read(path)

    config = {}

    config["webhook"] = str(parser["GENERAL"]["webhook"]).strip()
    config["cookie"] = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_" + str(parser["GENERAL"]["cookie"]).split("_")[-1]
    config["rolimons_update_interval"] = int(parser["GENERAL"]["rolimons_update_interval"])
    config["completed_trade_update_interval"] = int(parser["GENERAL"]["completed_trade_update_interval"])
    config["theme_name"] = str(parser["THEME"]["theme_name"])
    config["logging_level"] = int(parser["DEBUG"]["logging_level"])
    return config