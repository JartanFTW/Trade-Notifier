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

class Worker(self):

    @classmethod
    async def create(cls, user: User, webhook: str, rolimons_update_interval: int, completed_trade_update_interval: int, theme_name: str):
        
        self = Worker()

        self.user = user
        self.webhook = webhook
        self.rolimons_update_interval = rolimons_update_interval
        self.completed_trade_update_interval = completed_trade_update_interval
        self.theme_name = theme_name

        self.old_trades = []

        trade_datas = await self.user.get_trade_status_data(tradeStatusType = "Completed")
        for trade in trade_datas["data"][::-1]:
            self.old_trades.append(trade["id"])
    


    async def rolimons_loop(self):

        while True:

            self.roli_values = await get_roli_values

            await asyncio.sleep(self.rolimons_update_interval)
    


    async def completed_trade_loop(self):

        while True:
            
            print_timestamp("Checking confirmed trades")

            trades_data = await self.user.get_trade_status_data(tradeStatusType = "Completed")

            for trade in trades_data["data"][::-1]:

                if trade["id"] not in self.old_trades:

                    print_timestamp(f"Found new confirmed trade: {trade['id']}")

                    trade_data = await self.user.get_trade_data(trade["id"])

                    theme_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.theme_name)


                    #Making give and take item lists
                    give_items = []
                    take_items = []

                    for offer in trade["offers"]:

                        for item in offer["userAssets"]:

                            item_id = item["assetId"]

                            rap = self.roli_values["items"][item["assetId"]][2]

                            value = 0
                            if self.roli_values["items"][item["assetId"]][3] > 0:
                                value = self.roli_values["items"][item["assetId"]][3]
                            
                            if offer["user"]["id"] == self.user.id:

                                give_items.append({"id": item_id, "rap": rap, "roli_value": value})
                            
                            else:

                                take_items.append({"id": item_id, "rap": rap, "roli_value": value})


                    with open(os.path.join(theme_folder_path, "theme_setup.json")) as settings:
                        item_image_size = json.load(settings)["item_image_size"]

                    item_ids = give_items + take_items

                    item_image_urls = get_asset_image_url(item_ids = item_ids, size = item_image_size)

                    item_images = {}
                    for item in item_image_urls["data"]:
                        item_images[str(item["targetId"])] = await get_pillow_object_from_url(item["imageUrl"])
                    
                    
                    # Build image here

                    # Send webhook here









async def main():

    print_timestamp(f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW")
    logging.info(f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW")

    config = load_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "horizon_config.ini"))

    setup_logging(os.path.dirname(os.path.abspath(__file__)), level = config["logging_level"])







if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.critical(f"An unknown critical error occurred: {traceback.print_exc()}")
        print(f"An unknown critical error occurred: {traceback.print_exc()}")
    finally:
        input("Operations have complete. Press Enter to exit.")