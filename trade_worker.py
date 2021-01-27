import asyncio
import os
import traceback
import httpx
from user import User
from notification_builder import NotificationBuilder
from utilities import print_timestamp, get_roli_data, get_asset_image_url, get_pillow_object_from_url, construct_trade_data, send_trade_webhook, UnknownResponse


class TradeWorker():

    @classmethod
    async def create(cls, user: User, webhook_url: str, update_interval: int, theme_name: str, trade_type: str = "Completed", add_unvalued_to_value: bool = True, testing: bool = False):
        
        self = TradeWorker()

        self.user = user
        self.webhook_url = webhook_url
        self.update_interval = update_interval
        self.theme_name = theme_name
        self.trade_type = trade_type
        self.add_unvalued_to_value = add_unvalued_to_value

        self.old_completed_trades = []
        self.roli_data = None

        complete_trade_info = await self.user.get_trade_status_info(tradeStatusType=self.trade_type)
        for trade in complete_trade_info["data"][::-1]: # -1 to put old trades first in list, which are first to be removed
            self.old_completed_trades.append(trade["id"])

        if testing == True:
            print_timestamp(f"Testing mode enabled")
            del self.old_completed_trades[0]
        
        return self

    async def check_trade_loop(self):
        while True:
            try:
                print_timestamp(f"Checking {self.trade_type} trades")

                trades_info = await self.user.get_trade_status_info(tradeStatusType = self.trade_type)
                for trade in trades_info['data'][::-1]:
                    if trade['id'] not in self.old_completed_trades:
                        try:
                            self.roli_data = await get_roli_data()
                        except httpx.ReadTimeout:
                            print_timestamp(f"Couldn't grab Rolimons data. Connection timed out.")

                        self.old_completed_trades.append(trade["id"])
                        if len(self.old_completed_trades) > 10:
                            del self.old_completed_trades[0:-10]

                        print_timestamp(f"Detected new {self.trade_type} trade: {trade['id']}")

                        trade_info = await self.user.get_trade_info(trade["id"])
                        trade_data = construct_trade_data(trade_info, self.roli_data, self.user.id, add_unvalued_to_value=self.add_unvalued_to_value)

                        asset_ids = []
                        for offer in (trade_data['give'], trade_data['take']):
                            for item in offer['items'].values():
                                if str(item['assetId']) not in asset_ids:
                                    asset_ids.append(str(item['assetId']))

                        asset_images = {}
                        asset_image_urls = await get_asset_image_url(asset_ids = asset_ids, size = "700x700")
                        for item in asset_image_urls["data"]:
                            asset_images[str(item["targetId"])] = await get_pillow_object_from_url(item["imageUrl"])
                        
                        for offer in (trade_data['give'], trade_data['take']):
                            for item in offer['items'].values():
                                item['pillowImage'] = asset_images[str(item['assetId'])]
                        
                        themes_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")
                        theme_folder = os.path.join(themes_folder, self.theme_name)
                        builder = NotificationBuilder(theme_folder)
                        image_bytes = builder.build_image(trade_data)

                        try:

                            await send_trade_webhook(self.webhook_url, attachments = [("trade.png", image_bytes)])

                            print_timestamp(f"Sent {self.trade_type} trade webhook: {trade['id']}")

                        except UnknownResponse as e:

                            print_timestamp(f"Unable to send {self.trade_type} trade webhook: {trade['id']} got response {e.response_code}")
                
                await asyncio.sleep(self.update_interval)
            except Exception:
                print(traceback.print_exc())