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


# Standard Library
import asyncio
from configparser import ConfigParser
import logging
import os
import time

# Third-Party
from PIL import Image  # Actually using Pillow
import httpx

logger = logging.getLogger("horizon.utilities")


class UnknownResponse(Exception):
    def __init__(self, response_code: int, request_url: str, response_text: str = None):
        self.response_code = response_code
        self.request_url = request_url
        self.response_text = response_text
        self.err = f"An unhandled response {response_code} was received when calling {request_url}"
        logger.error(self.err)
        super().__init__(self.err)


class InvalidCookie(Exception):
    def __init__(self, response_code: int, request_url: str, response_text: str = None):
        self.response_code = response_code
        self.request_url = request_url
        self.response_text = response_text
        self.err = f"An invalid cookie was detected with response code {response_code} when calling {request_url}"
        logger.error(self.err)
        super().__init__(self.err)


def print_timestamp(text: str):
    """Prints to console the provided string with a H:M:S | timestamp before it"""
    print(time.strftime("%H:%M:%S | ", time.localtime()) + text)


async def get_asset_image_url(
    asset_ids: list,
    format: str = "Png",
    isCircular: str = "false",
    size: str = "110x110",
):
    """Grabs asset image urls from roblox using provided asset ids
    asset_ids should be a list of integer roblox asset ids
    format should be string either Png or Jpeg depending on if you want opacity or not
    isCircular should be a string either true or false no capitals based on if you want the image to be circular or not
    size should be a string and a size roblox supports. use google to find these or look here: https://thumbnails.roblox.com/docs#!/Assets/get_v1_assets
    Returns a dict:
    {
    "data": [
        {
        "targetId": 0,
        "state": "Error",
        "imageUrl": "string"
        }
    ]
    }
    """
    async with httpx.AsyncClient() as client:
        while True:
            logger.debug("Grabbing asset image urls")
            request = await client.get(
                f"https://thumbnails.roblox.com/v1/assets?assetIds={',+'.join(asset_ids)}&format={format}&isCircular={isCircular}&size={size}"
            )
            if request.status_code == 200:
                request_json = request.json()
                logger.info("Grabbed asset image urls")
                return request_json
            if request.status_code == 429:
                await asyncio.sleep(5)
                continue
            else:
                raise UnknownResponse(
                    request.status_code, request.url, response_text=request.text
                )


async def get_pillow_object_from_url(url: str):
    """Takes a url string containing an image and returns a pillow Image object"""
    async with httpx.AsyncClient() as client:
        while True:
            logger.debug(f"Creating pillow Image object from url {url}")
            request = await client.get(url)
            if request.status_code == 200:
                p_obj = Image.open(request)
                logger.info(f"Created pillow Image object from url: {url}")
                return p_obj
            if request.status_code == 429:
                await asyncio.sleep(5)
                continue
            else:
                raise UnknownResponse(
                    request.status_code, request.url, response_text=request.text
                )


async def send_trade_webhook(
    webhook_url: str, content: str = "", attachments: list = None
):
    """Sends a webhook to the provided url with the content and attachments provided
    webhook_url must be a string
    content must be a string and a maximum of 2000 characters else discord will respond badly
    attachments must be
    """
    files = {}
    for i in range(len(attachments)):
        files[f"file_{i}"] = (attachments[i][0], attachments[i][1])
    async with httpx.AsyncClient() as client:
        logger.debug("Sending trade webhook")
        request = await client.post(
            webhook_url, data={"content": content[:2000]}, files=files
        )
    if request.status_code == 200:
        logger.info("Sent trade webhook")
        return
    else:
        raise UnknownResponse(
            request.status_code, request.url, response_text=request.text
        )


async def get_roli_data():
    """Grabs rolimons itemdetails data and returns it as a dict"""
    async with httpx.AsyncClient() as client:
        logger.debug("Getting rolimon's data")
        request = await client.get("https://www.rolimons.com/itemapi/itemdetails")
    if request.status_code == 200:
        request_json = request.json()
        logger.info("Got rolimon's data")
        return request_json
    else:
        raise UnknownResponse(
            request.status_code, request.url, response_text=request.text
        )


def setup_logging(path: str, level: int = 40):
    """Sets up logging using basicConfig at level provided inside a logs folder created at the path string provided
    path must be a string and compatible with os module, and accessible by Horizon
    level must be an integer representing what level to log. See python Logging module documentation for details on this
    """
    logs_folder_path = os.path.join(path, "logs")
    if not os.path.exists(logs_folder_path):
        os.makedirs(logs_folder_path)
    log_path = os.path.join(
        logs_folder_path, time.strftime("%m %d %Y %H %M %S", time.localtime())
    )
    logging.basicConfig(
        filename=f"{log_path}.log",
        level=level,
        format="%(asctime)s:%(levelname)s:%(message)s",
    )


def load_config(path: str):
    """Loads config from path provided and returns it formatted for Horizon as a dict"""
    parser = ConfigParser()
    parser.read(path)
    config = {}

    config["cookie"] = (
        "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
        + str(parser["GENERAL"]["cookie"]).split("_")[-1]
    )
    config["add_unvalued_to_value"] = (
        True
        if str(parser["GENERAL"]["add_unvalued_to_value"]).upper() == "TRUE"
        else False
    )

    config["completed"] = {}
    config["completed"]["enabled"] = (
        True if str(parser["COMPLETED"]["enabled"]).upper() == "TRUE" else False
    )
    config["completed"]["webhook"] = str(parser["COMPLETED"]["webhook"]).strip()
    config["completed"]["update_interval"] = int(parser["COMPLETED"]["update_interval"])
    config["completed"]["theme_name"] = parser["COMPLETED"]["theme_name"]
    config["completed"]["webhook_content"] = parser["COMPLETED"]["webhook_content"]

    config["inbound"] = {}
    config["inbound"]["enabled"] = (
        True if str(parser["INBOUND"]["enabled"]).upper() == "TRUE" else False
    )
    config["inbound"]["webhook"] = str(parser["INBOUND"]["webhook"]).strip()
    config["inbound"]["update_interval"] = int(parser["INBOUND"]["update_interval"])
    config["inbound"]["theme_name"] = parser["INBOUND"]["theme_name"]
    config["inbound"]["webhook_content"] = parser["INBOUND"]["webhook_content"]

    config["outbound"] = {}
    config["outbound"]["enabled"] = (
        True if str(parser["OUTBOUND"]["enabled"]).upper() == "TRUE" else False
    )
    config["outbound"]["webhook"] = str(parser["OUTBOUND"]["webhook"]).strip()
    config["outbound"]["update_interval"] = int(parser["OUTBOUND"]["update_interval"])
    config["outbound"]["theme_name"] = parser["OUTBOUND"]["theme_name"]
    config["outbound"]["webhook_content"] = parser["OUTBOUND"]["webhook_content"]

    config["logging_level"] = int(parser["DEBUG"]["logging_level"])
    config["testing"] = (
        True if str(parser["DEBUG"]["testing"]).upper() == "TRUE" else False
    )
    config["double_check"] = (
        True if str(parser["DEBUG"]["double_check"]).upper() == "TRUE" else False
    )

    return config


def construct_trade_data(
    trade_info: dict,
    roli_data: dict,
    user_id: int,
    add_unvalued_to_value: bool,
    trade_status: str,
):
    """Inputs roblox trade data, rolimons data, 'self' user_id to mark one of the trade info people as user, and unvalued to value
    Outputs completely generated trade_data WITHOUT pillow images. After adding pillow images, ready to pass into NotificationBuilder
    """
    trade_data = {}
    trade_data["addUnvaluedToValue"] = add_unvalued_to_value
    trade_data["status"] = trade_status.lower().capitalize()
    trade_data["give"] = {}
    trade_data["take"] = {}

    for offer in trade_info["offers"]:
        side = "give"
        if offer["user"]["id"] != user_id:
            side = "take"

        trade_data[side]["user"] = offer["user"]

        trade_data[side]["items"] = {}
        for item_num in range(len(offer["userAssets"])):
            trade_data[side]["items"][
                f"item{item_num+1}"
            ] = {}  # Add + 1 so counting starts from 1 for user convenience

            for key, value in offer["userAssets"][item_num].items():
                trade_data[side]["items"][f"item{item_num+1}"][key] = value

            value = 0
            item_id = str(offer["userAssets"][item_num]["assetId"])
            if roli_data["items"][item_id][3] > 0:
                value = roli_data["items"][item_id][3]
            trade_data[side]["items"][f"item{item_num+1}"]["roliValue"] = value

        trade_data[side]["robux"] = offer["robux"]

    return trade_data


def format_text(text: str, trade_data: dict):
    """Formats different keywords for text stitching
    text is the string that needs formatting
    trade_data is a trade_data generated from construct_trade_data to use the details to format with
    Returns a formatted version of text
    """
    item_filter = ["item2", "item3", "item4"]
    var_filter = [
        "id",
        "serialNumber",
        "assetId",
        "name",
        "originalPrice",
        "assetStock",
    ]
    for side in ("give", "take"):
        for item in trade_data[side]["items"]:
            for key, value in trade_data[side]["items"][
                item
            ].items():  # Changing NoneTypes to empty strings so they show up as nothing on notification.
                if value == None:
                    trade_data[side]["items"][item][key] = ""
            if trade_data["addUnvaluedToValue"]:
                if trade_data[side]["items"][item]["roliValue"] == 0:
                    trade_data[side]["items"][item]["roliValue"] = trade_data[side][
                        "items"
                    ][item]["recentAveragePrice"]
        for (
            x
        ) in (
            item_filter
        ):  # Adding all items to dict so .format below doesn't scream IndexError. Can't just try/except it because then it won't work. If anyone has a better solution be my guest.
            if x not in trade_data[side]["items"]:
                trade_data[side]["items"][x] = {}
        for item in trade_data[side][
            "items"
        ].values():  # Making sure all used indexes are in items for above reason.
            for x in var_filter:
                if x not in item:
                    item[x] = ""
            for x in [
                "recentAveragePrice",
                "roliValue",
            ]:  # Same as above, but setting to 0 so total calculations don't scream.
                if x not in item:
                    item[x] = 0

    give_rap = sum(
        int(item["recentAveragePrice"]) for item in trade_data["give"]["items"].values()
    )
    take_rap = sum(
        int(item["recentAveragePrice"]) for item in trade_data["take"]["items"].values()
    )

    give_roli_value = sum(
        int(item["roliValue"]) for item in trade_data["give"]["items"].values()
    )
    take_roli_value = sum(
        int(item["roliValue"]) for item in trade_data["take"]["items"].values()
    )

    give_robux = str(trade_data["give"]["robux"])
    take_robux = str(trade_data["take"]["robux"])

    give_user_id = str(trade_data["give"]["user"]["id"])
    take_user_id = str(trade_data["take"]["user"]["id"])
    give_user_name = trade_data["give"]["user"]["name"]
    take_user_name = trade_data["take"]["user"]["name"]
    give_user_display_name = trade_data["give"]["user"]["displayName"]
    take_user_display_name = trade_data["take"]["user"]["displayName"]

    trade_status = trade_data["status"]

    text = text.format(
        give_rap=give_rap,
        take_rap=take_rap,
        give_roli_value=give_roli_value,
        take_roli_value=take_roli_value,
        give_robux=give_robux,
        take_robux=take_robux,
        give_user_id=give_user_id,
        take_user_id=take_user_id,
        give_user_name=give_user_name,
        take_user_name=take_user_name,
        give_user_display_name=give_user_display_name,
        take_user_display_name=take_user_display_name,
        trade_status=trade_status,
        give_item1_id=str(trade_data["give"]["items"]["item1"]["id"]),
        give_item2_id=str(trade_data["give"]["items"]["item2"]["id"]),
        give_item3_id=str(trade_data["give"]["items"]["item3"]["id"]),
        give_item4_id=str(trade_data["give"]["items"]["item4"]["id"]),
        take_item1_id=str(trade_data["take"]["items"]["item1"]["id"]),
        take_item2_id=str(trade_data["take"]["items"]["item2"]["id"]),
        take_item3_id=str(trade_data["take"]["items"]["item3"]["id"]),
        take_item4_id=str(trade_data["take"]["items"]["item4"]["id"]),
        give_item1_serial_number=str(
            trade_data["give"]["items"]["item1"]["serialNumber"]
        ),
        give_item2_serial_number=str(
            trade_data["give"]["items"]["item2"]["serialNumber"]
        ),
        give_item3_serial_number=str(
            trade_data["give"]["items"]["item3"]["serialNumber"]
        ),
        give_item4_serial_number=str(
            trade_data["give"]["items"]["item4"]["serialNumber"]
        ),
        take_item1_serial_number=str(
            trade_data["take"]["items"]["item1"]["serialNumber"]
        ),
        take_item2_serial_number=str(
            trade_data["take"]["items"]["item2"]["serialNumber"]
        ),
        take_item3_serial_number=str(
            trade_data["take"]["items"]["item3"]["serialNumber"]
        ),
        take_item4_serial_number=str(
            trade_data["take"]["items"]["item4"]["serialNumber"]
        ),
        give_item1_asset_id=str(trade_data["give"]["items"]["item1"]["assetId"]),
        give_item2_asset_id=str(trade_data["give"]["items"]["item2"]["assetId"]),
        give_item3_asset_id=str(trade_data["give"]["items"]["item3"]["assetId"]),
        give_item4_asset_id=str(trade_data["give"]["items"]["item4"]["assetId"]),
        take_item1_asset_id=str(trade_data["take"]["items"]["item1"]["assetId"]),
        take_item2_asset_id=str(trade_data["take"]["items"]["item2"]["assetId"]),
        take_item3_asset_id=str(trade_data["take"]["items"]["item3"]["assetId"]),
        take_item4_asset_id=str(trade_data["take"]["items"]["item4"]["assetId"]),
        give_item1_name=trade_data["give"]["items"]["item1"]["name"],
        give_item2_name=trade_data["give"]["items"]["item2"]["name"],
        give_item3_name=trade_data["give"]["items"]["item3"]["name"],
        give_item4_name=trade_data["give"]["items"]["item4"]["name"],
        take_item1_name=trade_data["take"]["items"]["item1"]["name"],
        take_item2_name=trade_data["take"]["items"]["item2"]["name"],
        take_item3_name=trade_data["take"]["items"]["item3"]["name"],
        take_item4_name=trade_data["take"]["items"]["item4"]["name"],
        give_item1_recent_average_price=str(
            trade_data["give"]["items"]["item1"]["recentAveragePrice"]
        ),
        give_item2_recent_average_price=str(
            trade_data["give"]["items"]["item2"]["recentAveragePrice"]
        ),
        give_item3_recent_average_price=str(
            trade_data["give"]["items"]["item3"]["recentAveragePrice"]
        ),
        give_item4_recent_average_price=str(
            trade_data["give"]["items"]["item4"]["recentAveragePrice"]
        ),
        take_item1_recent_average_price=str(
            trade_data["take"]["items"]["item1"]["recentAveragePrice"]
        ),
        take_item2_recent_average_price=str(
            trade_data["take"]["items"]["item2"]["recentAveragePrice"]
        ),
        take_item3_recent_average_price=str(
            trade_data["take"]["items"]["item3"]["recentAveragePrice"]
        ),
        take_item4_recent_average_price=str(
            trade_data["take"]["items"]["item4"]["recentAveragePrice"]
        ),
        give_item1_original_price=str(
            trade_data["give"]["items"]["item1"]["originalPrice"]
        ),
        give_item2_original_price=str(
            trade_data["give"]["items"]["item2"]["originalPrice"]
        ),
        give_item3_original_price=str(
            trade_data["give"]["items"]["item3"]["originalPrice"]
        ),
        give_item4_original_price=str(
            trade_data["give"]["items"]["item4"]["originalPrice"]
        ),
        take_item1_original_price=str(
            trade_data["take"]["items"]["item1"]["originalPrice"]
        ),
        take_item2_original_price=str(
            trade_data["take"]["items"]["item2"]["originalPrice"]
        ),
        take_item3_original_price=str(
            trade_data["take"]["items"]["item3"]["originalPrice"]
        ),
        take_item4_original_price=str(
            trade_data["take"]["items"]["item4"]["originalPrice"]
        ),
        give_item1_asset_stock=str(trade_data["give"]["items"]["item1"]["assetStock"]),
        give_item2_asset_stock=str(trade_data["give"]["items"]["item2"]["assetStock"]),
        give_item3_asset_stock=str(trade_data["give"]["items"]["item3"]["assetStock"]),
        give_item4_asset_stock=str(trade_data["give"]["items"]["item4"]["assetStock"]),
        take_item1_asset_stock=str(trade_data["take"]["items"]["item1"]["assetStock"]),
        take_item2_asset_stock=str(trade_data["take"]["items"]["item2"]["assetStock"]),
        take_item3_asset_stock=str(trade_data["take"]["items"]["item3"]["assetStock"]),
        take_item4_asset_stock=str(trade_data["take"]["items"]["item4"]["assetStock"]),
        give_item1_roli_value=str(trade_data["give"]["items"]["item1"]["roliValue"]),
        give_item2_roli_value=str(trade_data["give"]["items"]["item2"]["roliValue"]),
        give_item3_roli_value=str(trade_data["give"]["items"]["item3"]["roliValue"]),
        give_item4_roli_value=str(trade_data["give"]["items"]["item4"]["roliValue"]),
        take_item1_roli_value=str(trade_data["take"]["items"]["item1"]["roliValue"]),
        take_item2_roli_value=str(trade_data["take"]["items"]["item2"]["roliValue"]),
        take_item3_roli_value=str(trade_data["take"]["items"]["item3"]["roliValue"]),
        take_item4_roli_value=str(trade_data["take"]["items"]["item4"]["roliValue"]),
    )

    return text


async def check_for_update(current_version: str):
    """Checks if provided current_version variable matches that of tag_name on the latest release GitHub API. Returns True if there is an update, False if there is not."""
    async with httpx.AsyncClient() as client:
        logger.info("Checking for Horizon update")
        request = await client.get(
            "https://api.github.com/repos/JartanFTW/Trade-Notifier/releases/latest"
        )
    if request.status_code == 200:
        if current_version != request.json()["tag_name"]:
            return True
        else:
            return False
    else:
        raise UnknownResponse(
            request.response_code, request.url, response_text=request.text
        )