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


import asyncio
from configparser import ConfigParser
import logging
import os
from PIL import Image
import time
import httpx

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



async def get_asset_image_url(asset_ids: list, format: str = "Png", isCircular: str = "false", size: str = "110x110"):

    async with httpx.AsyncClient() as client:
        
        while True:

            logger.info("Grabbing asset image urls")

            request = await client.get(f"https://thumbnails.roblox.com/v1/assets?assetIds={',+'.join(asset_ids)}&format={format}&isCircular={isCircular}&size={size}")

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



async def send_trade_webhook(webhook_url: str, content: str = "", attachments: list = None): # TODO Rewrite properly utilizing **kwargs for custom request stuffs.

    files = {}
    for i in range(len(attachments)):
        files[f"file_{i}"] = (attachments[i][0], attachments[i][1])

    async with httpx.AsyncClient() as client:

        logger.info("Sending trade webhook")

        request = await client.post(webhook_url, data={"content": content}, files = files)
    
    if request.status_code == 200:

        logger.debug("Sent trade webhook")

        return

    else:

        logger.error("Failed to send trade webhook")

        raise UnknownResponse(request.status_code, request.url, response_text = request.text)



async def get_roli_data():

    async with httpx.AsyncClient() as client:

        logger.info("Getting rolimon's data")

        request = await client.get("https://www.rolimons.com/itemapi/itemdetails")

    if request.status_code == 200:

        request_json = request.json()

        logger.debug(f"Got rolimon's data: {request_json}")

        return request_json
    
    else:

        logger.critical(f"Failed to update rolimon's data: {request.status_code}")

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

    config['cookie'] = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_" + str(parser['GENERAL']['cookie']).split("_")[-1]
    config['add_unvalued_to_value'] = True if str(parser['GENERAL']['add_unvalued_to_value']).upper() == "TRUE" else False

    config['completed'] = {}
    config['completed']['enabled'] = True if str(parser['COMPLETED']['enabled']).upper() == "TRUE" else False
    config['completed']['webhook'] = str(parser['COMPLETED']['webhook']).strip()
    config['completed']['update_interval'] = int(parser['COMPLETED']['update_interval'])
    config['completed']['theme_name'] = parser['COMPLETED']['theme_name']
    config['completed']['webhook_content'] = parser['COMPLETED']['webhook_content']

    config['inbound'] = {}
    config['inbound']['enabled'] = True if str(parser['INBOUND']['enabled']).upper() == "TRUE" else False
    config['inbound']['webhook'] = str(parser['INBOUND']['webhook']).strip()
    config['inbound']['update_interval'] = int(parser['INBOUND']['update_interval'])
    config['inbound']['theme_name'] = parser['INBOUND']['theme_name']
    config['inbound']['webhook_content'] = parser['INBOUND']['webhook_content']

    config['logging_level'] = int(parser['DEBUG']['logging_level'])
    config['testing'] = True if str(parser['DEBUG']['testing']).upper() == "TRUE" else False
    
    return config



def construct_trade_data(trade_info: dict, roli_data: dict, user_id: int, add_unvalued_to_value: bool):
    """Inputs roblox trade data, rolimons data, 'self' user_id to mark one of the trade info people as user, and unvalued to value
    Outputs completely generated trade_data WITHOUT pillow images. After adding pillow images, ready to pass into NotificationBuilder
    """
    trade_data = {}
    trade_data['addUnvaluedToValue'] = add_unvalued_to_value
    trade_data['status'] = trade_info['status']
    trade_data['give'] = {}
    trade_data['take'] = {}

    for offer in trade_info['offers']:
        side = "give"
        if offer['user']['id'] != user_id:
            side = "take"
        
        trade_data[side]['user'] = offer['user']

        trade_data[side]['items'] = {}
        for item_num in range(len(offer['userAssets'])):
            trade_data[side]['items'][f'item{item_num+1}'] = {} # Add + 1 so counting starts from 1 for user convenience

            for key, value in offer['userAssets'][item_num].items():
                trade_data[side]['items'][f'item{item_num+1}'][key] = value

            value = 0
            item_id = str(offer['userAssets'][item_num]['assetId'])
            if roli_data['items'][item_id][3] > 0:
                value = roli_data["items"][item_id][3]
            trade_data[side]['items'][f'item{item_num+1}']['roliValue'] = value
        
        trade_data[side]['robux'] = offer['robux']
    
    return trade_data