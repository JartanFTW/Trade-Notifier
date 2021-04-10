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
import logging
import os
import traceback

# Third Party
from discord import Webhook, File
import httpx

# Local
from user import User
from notification_builder import NotificationBuilder
from utilities import (
    print_timestamp,
    get_roli_data,
    get_asset_image_url,
    get_pillow_object_from_url,
    construct_trade_data,
    UnknownResponse,
    format_text,
    HttpxWebhookAdapter,
)

logger = logging.getLogger("horizon.main")


class TradeWorker:
    @classmethod
    async def create(
        cls,
        main_folder_path: str,
        user: User,
        webhook_url: str,
        update_interval: int,
        theme_name: str,
        trade_type: str = "Completed",
        add_unvalued_to_value: bool = True,
        testing: bool = False,
        double_check: bool = False,
        webhook_content: str = "",
        max_username_length: int = 20,
    ):
        self = TradeWorker()
        self.main_folder_path = main_folder_path
        self.user = user
        self.webhook_url = webhook_url
        self.update_interval = update_interval
        self.theme_name = theme_name
        self.trade_type = trade_type
        self.add_unvalued_to_value = add_unvalued_to_value
        self.double_check = double_check
        self.webhook_content = webhook_content
        self.max_username_length = max_username_length

        self.old_trades = []
        self.roli_data = None
        old_trade_info = await self.user.get_trade_status_info(
            tradeStatusType=self.trade_type, limit=25
        )
        for trade in old_trade_info["data"][
            ::-1
        ]:  # ::-1 to put old trades first in list, which are first to be removed
            self.old_trades.append(trade["id"])

        if testing:
            print_timestamp(
                f"{self.user.display_name:>{self.max_username_length}} | {self.trade_type} testing mode enabled"
            )
            try:
                asyncio.create_task(self.send_trade(old_trade_info["data"][0]))
            except IndexError:
                logger.warning(
                    f"{self.user.display_name:>{self.max_username_length}} | No {self.trade_type} trades in history to send test webhook based on"
                )
                print_timestamp(
                    f"{self.user.display_name:>{self.max_username_length}} | No {self.trade_type} trades in history to send test webhook based on"
                )
        return self

    async def send_trade(self, trade):
        if self.double_check:
            print_timestamp(
                f"{self.user.display_name:>{self.max_username_length}} | Double-checking {self.trade_type} trade: {trade['id']}"
            )
            await asyncio.sleep(10)
            while True:
                try:
                    trades_info = await self.user.get_trade_status_info(
                        tradeStatusType=self.trade_type
                    )
                    break
                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
                    logger.warning(
                        f"{self.user.display_name:>{self.max_username_length}} | Timed out while trying to grab {self.trade_type} trade status info: {traceback.format_exc()}"
                    )
                    print_timestamp(
                        f"{self.user.display_name:>{self.max_username_length}} | Timed out while trying to grab {self.trade_type} trade status info"
                    )
                    await asyncio.sleep(5)
            if trade["id"] not in [trade["id"] for trade in trades_info["data"][::-1]]:
                print_timestamp(
                    f"{self.user.display_name:>{self.max_username_length}} | {self.trade_type} trade {trade['id']} detected as fake, skipping notification"
                )
                return

        try:
            self.roli_data = await get_roli_data()
        except httpx.ReadTimeout:
            logger.error(
                f"{self.user.display_name:>{self.max_username_length}} | Timed out while trying to grab roli data: {traceback.format_exc()}"
            )
            print_timestamp(
                f"{self.user.display_name:>{self.max_username_length}} | Timed out while trying to grab roli data"
            )
        except Exception:
            logger.error(
                f"{self.user.display_name:>{self.max_username_length}} | Unknown error while grabbing rolimons data: {traceback.format_exc()}"
            )

        trade_info = await self.user.get_trade_info(trade["id"])
        trade_data = construct_trade_data(
            trade_info,
            self.roli_data,
            self.user.id,
            self.add_unvalued_to_value,
            self.trade_type,
        )

        asset_ids = []
        for offer in (trade_data["give"], trade_data["take"]):
            for item in offer["items"].values():
                if str(item["assetId"]) not in asset_ids:
                    asset_ids.append(str(item["assetId"]))

        asset_images = {}
        asset_image_urls = await get_asset_image_url(
            asset_ids=asset_ids, size="700x700"
        )
        for item in asset_image_urls["data"]:
            asset_images[str(item["targetId"])] = await get_pillow_object_from_url(
                item["imageUrl"]
            )
        for offer in (trade_data["give"], trade_data["take"]):
            for item in offer["items"].values():
                item["pillowImage"] = asset_images[str(item["assetId"])]

        themes_folder = os.path.join(self.main_folder_path, "themes")
        theme_folder = os.path.join(themes_folder, self.theme_name)
        builder = NotificationBuilder(theme_folder)
        image_bytes = builder.build_image(trade_data)
        content = format_text(self.webhook_content, trade_data)

        async with httpx.AsyncClient() as client:
            webhook = Webhook.from_url(
                self.webhook_url, adapter=HttpxWebhookAdapter(client)
            )
            await webhook.send(
                content=content,
                file=File(image_bytes, filename="trade.png"),
            )
        logger.info(
            f"{self.user.display_name:>{self.max_username_length}} | Sent {self.trade_type} trade webhook: {trade['id']}"
        )
        print_timestamp(
            f"{self.user.display_name:>{self.max_username_length}} | Sent {self.trade_type} trade webhook: {trade['id']}"
        )

    async def check_trade_loop(self):
        while True:
            print_timestamp(
                f"{self.user.display_name:>{self.max_username_length}} | Checking {self.trade_type} trades"
            )
            try:
                trades_info = await self.user.get_trade_status_info(
                    tradeStatusType=self.trade_type
                )
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError):
                logger.warning(
                    f"{self.user.display_name:>{self.max_username_length}} | Timed out while trying to grab {self.trade_type} trade status info: {traceback.format_exc()}"
                )
                print_timestamp(
                    f"{self.user.display_name:>{self.max_username_length}} | Timed out while trying to grab {self.trade_type} trade status info"
                )
                await asyncio.sleep(self.update_interval)
                continue

            for trade in trades_info["data"][::-1]:
                if trade["id"] not in self.old_trades:
                    print_timestamp(
                        f"{self.user.display_name:>{self.max_username_length}} | Detected new {self.trade_type} trade: {trade['id']}"
                    )
                    self.old_trades.append(trade["id"])
                    if len(self.old_trades) > 25:
                        del self.old_trades[0:-25]
                    asyncio.create_task(self.send_trade(trade))
            await asyncio.sleep(self.update_interval)