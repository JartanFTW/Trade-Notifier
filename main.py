import httpx
import json
from configparser import ConfigParser
import logging
import os
import time
import asyncio
import traceback
import PIL
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import sys

print("Horizon Trade Notifier - Jartan#7450 - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW")

clear = lambda: os.system("cls")

def print_console(text, logging_level=20):
    print(time.strftime('%H:%M:%S | ', time.localtime()) + str(text))
    logging.log(logging_level, str(text))

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
    config["cookie"] = ".ROBLOSECURITY=_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_" + str(parser["GENERAL"]["cookie"]).split("_")[-1] + ";"
    config["rolimons_update_interval"] = int(parser["GENERAL"]["rolimons_update_interval"])
    config["completed_trade_update_interval"] = int(parser["GENERAL"]["completed_trade_update_interval"])
    config["logging_level"] = int(parser["DEBUG"]["logging_level"])
    return config

class Worker():

    def __init__(self, webhook, cookie, rolimons_update_interval, completed_trade_update_interval):
        self.webhook = webhook
        self.cookie = cookie
        self.rolimons_update_interval = rolimons_update_interval
        self.completed_trade_update_interval = completed_trade_update_interval
    
    async def async_init(self):
        self.client = httpx.AsyncClient()
        
        print_console("Performing initialization csrf update.", 20)
        await self.update_csrf()

        logging.debug(f"Initialization csrf token: {self.csrf}")

        print_console("Performing initialization trades grab.", 20)
        self.old_trades = []
        trades_json = await self.get_completed_trades()
        for trade in trades_json["data"][::-1]:
            self.old_trades.append(trade["id"])
        
        logging.debug(f"Initialization trade request json: {trades_json}")
        logging.debug(f"Initialization old_trades: {self.old_trades}")
    

    async def grab_rolimons_values(self):

        request = await self.client.get("https://www.rolimons.com/itemapi/itemdetails")

        request_json = request.json()

        return request_json["items"]
    
    async def rolimons_loop(self):
        while True:

            self.roli_values = await self.grab_rolimons_values()

            print_console("Updated rolimons values.", 20)

            await asyncio.sleep(self.rolimons_update_interval)
    
    async def update_csrf(self):

        while True:

            request = await self.client.post("https://auth.roblox.com/v1/logout", headers={"Cookie": self.cookie})

            try:

                self.csrf = request.headers["x-csrf-token"]

                print_console(f"Updated csrf token: {self.csrf}", 20)

                return

            except KeyError:

                if request.status_code == 429:
                    
                    logging.info("Couldn't update csrf token: 429")

                    continue
                
                if request.status_code == 401:

                    logging.critical("Couldn't update csrf token: 401")

                    print_console("Cookie is invalid.", 50)

                    await self.client.aclose()

                    sys.exit()
                
                else:

                    print_console(f"An unknown critical error occurred while updating csrf token. Unknown response code: {request.status_code}", 50)

                    await self.client.aclose()

                    sys.exit()

    async def get_completed_trades(self):

        request = await self.client.get("https://trades.roblox.com/v1/trades/Completed?limit=10&sortOrder=Asc", headers={"Cookie": self.cookie, "X-CSRF-TOKEN": self.csrf})

        request_json = request.json()

        logging.debug(f"Completed trades json: {request_json}")

        return request_json
    
    async def get_trade_data(self, trade_id):
        request = await self.client.get(f"https://trades.roblox.com/v1/trades/{trade_id}", headers={"Cookie": self.cookie, "X-CSRF-TOKEN": self.csrf})

        request_json = request.json()

        logging.debug(f"Trade details json: {request_json}")

        return request_json

    async def get_asset_images_urls(self, ids):
        request = await self.client.get(f"https://thumbnails.roblox.com/v1/assets?assetIds={',+'.join(ids)}&format=Png&isCircular=false&size=110x110")

        request_json = request.json()

        return request_json
    
    async def get_asset_image_object(self, url):
        request = await self.client.get(url)

        image = Image.open(request)

        return image


    async def generate_image(self, trade): #TODO REWORK TO ALLOW CONFIG CUSTOM BACKGROUNDS

        id_list = []

        for offer in trade["offers"]:
            for item in offer["userAssets"]:
                id_list.append(str(item["assetId"]))

        image_urls = await self.get_asset_images_urls(id_list)

        trade_image = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "background.png"))

        image_objects = {}
        for item in image_urls["data"]:
            if item["state"] == "Completed":
                image_objects[str(item["targetId"])] = await self.get_asset_image_object(item["imageUrl"])
        
        for i in range(len(trade["offers"][0]["userAssets"])):

            item = trade["offers"][0]["userAssets"][i]
           
            try:
                trade_image.paste(image_objects[str(item["assetId"])], mask = image_objects[str(item["assetId"])], box=(75 + 120*i + 30*i, 85))
            except KeyError:
                continue
        
        for i in range(len(trade["offers"][1]["userAssets"])):

            item = trade["offers"][1]["userAssets"][i]

            try:
                trade_image.paste(image_objects[str(item["assetId"])], mask = image_objects[str(item["assetId"])], box=(75 + 120*i + 30*i, 345))
            except KeyError:
                continue
        
        draw = ImageDraw.Draw(trade_image)
        font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rubik-Medium.ttf"), 25)

        rap_offered = 0
        value_offered = 0

        for item in trade["offers"][0]["userAssets"]:
            rap_offered += self.roli_values[str(item["assetId"])][2]
            if self.roli_values[str(item["assetId"])][3] > 0:
                value_offered += self.roli_values[str(item["assetId"])][3]

    
        rap_received = 0
        value_received = 0

        for item in trade["offers"][1]["userAssets"]:
            rap_received += self.roli_values[str(item["assetId"])][2]
            if self.roli_values[str(item["assetId"])][3] > 0:
                value_received += self.roli_values[str(item["assetId"])][3]

        draw.text((650, 85), f"Rap offered: {rap_offered}", font=font, fill = (0, 128, 0))
        draw.text((650, 345), f"Rap offered: {rap_received}", font=font, fill = (0, 128, 0))
        draw.text((650, 130), f"Value offered: {value_offered}", font=font, fill = (0, 128, 255))
        draw.text((650, 400), f"Value offered: {value_received}", font=font, fill = (0, 128, 255))

        return trade_image

    async def send_webhook(self, pillow_image):

        attachment = BytesIO()

        pillow_image.save(attachment, "png")

        attachment.seek(0)

        request = await self.client.post(self.webhook, files={"file1": ("trade.png", attachment)})
        
        if request.status_code != 200:
            print(f"Unable to send webhook: {request.status_code}")
    

    async def check_confirmed_trades_loop(self):
                                        
        if not isinstance(self.csrf, str):
            await self.update_csrf()

        while True:
                                        
            print_console("Checking confirmed trades.", 20)

            trades_json = await self.get_completed_trades()
            for trade in trades_json["data"][::-1]:
                if trade["id"] not in self.old_trades:

                    print_console(f"Found new confirmed trade: {trade['id']}", 20)

                    trade_data = await self.get_trade_data(trade["id"])

                    trade_picture = await self.generate_image(trade_data)

                    await self.send_webhook(trade_picture)
                                        
                    print_console("Sent confirmed trade webhook.", 20)

                    self.old_trades.append(trade["id"])

                    if len(self.old_trades) > 10:
                        del self.old_trades[0:-10]
                    
                    logging.debug(f"Updated old trades: {self.old_trades}")
            
            await asyncio.sleep(self.completed_trade_update_interval)
    
    async def run_workers(self):

        tasks = []
        tasks.append(asyncio.create_task(self.rolimons_loop()))
        tasks.append(asyncio.create_task(self.check_confirmed_trades_loop()))

        await asyncio.wait(tasks)
        await self.client.aclose()


async def main():

    config = load_config()

    setup_logging(config["logging_level"])

    worker = Worker(config["webhook"], config["cookie"], config["rolimons_update_interval"], config["completed_trade_update_interval"])

    await worker.async_init()
    
    await worker.run_workers()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.critical(f"An unknown critical error occurred: {traceback.print_exc()}")
        print(f"An unknown critical error occurred: {traceback.print_exc()}")
    finally:
        input("Operations have complete. Press Enter to exit.")