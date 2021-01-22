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



import httpx
import json
from configparser import ConfigParser
import logging
import os
import asyncio
import traceback
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import sys
from image_builder import ImageBuilder
from utilities import *
from user import User

version = "v0.2.0-alpha"

logger = logging.getLogger("horizon.main")

class Worker():

    @classmethod
    async def create(cls, user: User, webhook_url: str, rolimons_update_interval: int, completed_trade_update_interval: int, theme_name: str):
        
        self = Worker()

        self.user = user
        self.webhook_url = webhook_url
        self.rolimons_update_interval = rolimons_update_interval
        self.completed_trade_update_interval = completed_trade_update_interval
        self.theme_name = theme_name

        self.old_trades = []
        self.roli_values = None

        trade_datas = await self.user.get_trade_status_data(tradeStatusType = "Completed")
        for trade in trade_datas["data"][::-1]:
            self.old_trades.append(trade["id"])
        
        return self
    


    async def rolimons_loop(self):

        while True:

            self.roli_values = await get_roli_values()

            await asyncio.sleep(self.rolimons_update_interval)
    


    async def completed_trade_loop(self):
        while True: # Making sure roli values are initialized
            if isinstance(self.roli_values, dict):
                break
            self.roli_values = await get_roli_values()

        while True:
            
            print_timestamp("Checking confirmed trades")

            trades_data = await self.user.get_trade_status_data(tradeStatusType = "Completed")

            for trade in trades_data["data"][::-1]:

                if trade["id"] not in self.old_trades:

                    self.old_trades.append(trade["id"])

                    if len(self.old_trades) > 10:
                        del self.old_trades[0:-10]

                    print_timestamp(f"Found new confirmed trade: {trade['id']}")

                    trade_data = await self.user.get_trade_data(trade["id"])

                    themes_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")

                    theme_folder_path = os.path.join(themes_folder_path, self.theme_name)

                    # Creating give and take item lists
                    give_items = []
                    take_items = []
                    try:
                        for offer in trade_data["offers"]:

                            for item in offer["userAssets"]:

                                item_id = item["assetId"]

                                rap = self.roli_values["items"][str(item["assetId"])][2]

                                value = 0
                                if self.roli_values["items"][str(item["assetId"])][3] > 0:
                                    value = self.roli_values["items"][str(item["assetId"])][3]
                                
                                if offer["user"]["id"] == self.user.id:

                                    give_items.append({"id": item_id, "rap": rap, "roli_value": value})
                                
                                else:

                                    take_items.append({"id": item_id, "rap": rap, "roli_value": value})

                        # Loading image size
                        with open(os.path.join(theme_folder_path, "theme_setup.json")) as settings:
                            item_image_size = json.load(settings)["item_image_size"]


                        # Getting item images
                        item_ids = [str(item["id"]) for item in give_items + take_items]

                        item_image_urls = await get_asset_image_url(item_ids = item_ids, size = item_image_size)

                        item_images = {}
                        for item in item_image_urls["data"]:
                            item_images[str(item["targetId"])] = await get_pillow_object_from_url(item["imageUrl"])


                        # Building image
                        builder = ImageBuilder()
                        trade_image = builder.build_image(theme_folder_path, give_items, take_items, item_images)


                        try:

                            await send_trade_webhook(self.webhook_url, attachments = [("trade.png", trade_image)])

                            print_timestamp(f"Sent confirmed trade webhook: {trade['id']}")

                        except UnknownResponse as e:

                            print_timestamp(f"Unable to send trade webhook: {trade['id']} got response {e.response_code}")
                    except Exception:
                        print(traceback.print_exc())
            
            await asyncio.sleep(self.completed_trade_update_interval)



async def main():

    config = load_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "horizon_config.ini"))

    setup_logging(os.path.dirname(os.path.abspath(__file__)), level = config["logging_level"])

    print_timestamp(f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW")
    logging.info(f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW")

    user = await User.create(config["cookie"])

    worker = await Worker.create(user, config["webhook"], config["rolimons_update_interval"], config["completed_trade_update_interval"], config["theme_name"])

    tasks = []

    tasks.append(asyncio.create_task(worker.rolimons_loop()))
    tasks.append(asyncio.create_task(worker.completed_trade_loop()))

    await asyncio.wait(tasks)









if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.critical(f"An unknown critical error occurred: {traceback.print_exc()}")
        print(f"An unknown critical error occurred: {traceback.print_exc()}")
    finally:
        input("Operations have complete. Press Enter to exit.")