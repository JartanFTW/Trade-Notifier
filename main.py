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
        await self.update_csrf()
        self.old_trades = []
        trades_json = await self.get_completed_trades()
        for trade in trades_json["data"]:
            self.old_trades.append(trade["id"])
    

    async def grab_rolimons_values(self):

        request = await self.client.get("https://www.rolimons.com/itemapi/itemdetails")

        request_json = request.json()

        return request_json["items"]
    
    async def rolimons_loop(self):
        while True:

            self.roli_values = await self.grab_rolimons_values()

            await asyncio.sleep(self.rolimons_update_interval)
    
    async def update_csrf(self):

        request = await self.client.post("https://auth.roblox.com/v1/logout", headers={"Cookie": self.cookie})

        try:

            self.csrf = request.headers["x-csrf-token"]

        except IndexError:

            status = await request.status_code

            return status

    async def get_completed_trades(self):

        request = await self.client.get("https://trades.roblox.com/v1/trades/Completed?limit=10&sortOrder=Asc", headers={"Cookie": self.cookie, "X-CSRF-TOKEN": self.csrf})

        request_json = request.json()

        return request_json
    
    async def get_trade_data(self, trade_id):
        request = await self.client.get(f"https://trades.roblox.com/v1/trades/{trade_id}", headers={"Cookie": self.cookie, "X-CSRF-TOKEN": self.csrf})

        request_json = request.json()

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
            value_offered += self.roli_values[str(item["assetId"])][3] # TODO MAKE NOT TAKE INTO ACCOUNT NEGATIVE (undefined) VALUES (-1)
    
        rap_received = 0
        value_received = 0

        for item in trade["offers"][1]["userAssets"]:
            rap_received += self.roli_values[str(item["assetId"])][2]
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

            trades_json = await self.get_completed_trades()
            for trade in trades_json["data"]:
                if trade["id"] not in self.old_trades:

                    trade_data = await self.get_trade_data(trade["id"])

                    trade_picture = await self.generate_image(trade_data)


                    await self.send_webhook(trade_picture)

                    self.old_trades.append(trade["id"])

                    if len(self.old_trades) > 10:
                        del self.old_trades[0:-11]
            
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
        input("Operations have complete.")