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
from datetime import datetime
import logging
from typing import Literal

# Third Party
import httpx

# Local
from .errors import UnknownResponse, InvalidCookie

log = logging.getLogger(__name__)


class User:
    def __init__(self):
        pass

    @classmethod
    async def create(cls, security_cookie: str):
        """Factory method to allow for async initialization of User object.
        security_cookie should be formatted as: "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_xyz123"
        Returns a User() object.
        """
        log.debug("Creating roblox user object")
        self = User()

        self.client = httpx.AsyncClient(cookies={})
        self.client.cookies[".ROBLOSECURITY"] = security_cookie

        await self.__authenticate()

        log.info(f"Created roblox user object: {self.id}")
        return self

    async def __request(self, method: str, url: str, **kwargs):
        method = method.lower()

        resp = await self.client.Request(method, url, url, **kwargs)
        if method != "get":
            if "x-csrf-token" in resp.headers.keys():
                self.client.cookies["X-CSRF-TOKEN"] = resp.headers["x-csrf-token"]
                if resp.status_code == 403:
                    resp = await self.client.Request(method, url, **kwargs)

        if resp.status_code == 401:
            raise InvalidCookie(
                resp.cookies[".ROBLOSECURITY"], resp.response_code, resp.url
            )

        return resp

    async def __authenticate(self):
        while True:
            resp = await self.client.__request(
                "get", "https://users.roblox.com/v1/users/authenticated"
            )
            if resp.status_code != 429:
                break
            await asyncio.sleep(1)
        if resp.status_code != 200:
            raise UnknownResponse(resp.status_code, resp.url, resp.text)
        else:
            resp_json = resp.json()
            self.id = resp_json["id"]
            self.name = resp_json["name"]
            self.display_name = resp_json["displayName"]

    async def get_trades(
        self,
        status_type: Literal["Inbound", "Outbound", "Completed"] = "Inbound",
        limit: Literal[10, 25, 50, 100] = 10,
        sort_order: Literal["Asc", "Desc"] = "Asc",
    ) -> dict:
        """Fetches a list of authenticated user's trades
        https://trades.roblox.com/docs#!/Trades/get_v1_trades_tradeStatusType
        """
        log.debug(f"Fetching user trades {status_type}")
        while True:
            resp = await self.__request(
                "get",
                f"https://trades.roblox.com/v1/trades/{status_type}?limit={limit}&sortOrder={sort_order}",
            )
            if resp.status_code == 429:
                await asyncio.sleep(1)
                continue
            break
        if resp.status_code == 200:
            log.debug(f"Grabbed user trade {status_type}")
            return resp.json()
        raise UnknownResponse(resp.status_code, resp.url, resp.text)

    async def get_trade(self, trade_id: int) -> dict:
        """Gets detailed information about a trade
        https://trades.roblox.com/docs#!/Trades/get_v1_trades_tradeId
        """
        log.debug(f"Fetching trade information {trade_id}")
        while True:
            resp = await self.__request(
                "get", f"https://trades.roblox.com/v1/trades/{trade_id}"
            )
            if resp.status_code == 429:
                await asyncio.sleep(1)
                continue
            break
        if resp.status_code == 200:
            request_json = resp.json()
            log.debug(f"Fetched user trade info {trade_id}")
            return resp.json()
        raise UnknownResponse(resp.status_code, resp.url, resp.text)


class Item:
    def __init__(
        self,
        id: int,
        name: str,
        recent_average_price: int,
        serial_number: int = None,
        asset_id: int = None,
        rolimons_value: int = None,
        **kwargs,
    ):
        self.__dict__ |= kwargs
        self.id = id
        self.name = name
        self.recent_average_price = recent_average_price
        self.serial_number = serial_number
        self.asset_id = asset_id
        self.rolimons_value = rolimons_value


class Trade:
    def __init__(
        self,
        data: dict,
        sender: User,
        offer_items: list[Item],
        receive_items: list[Item],
    ):
        self.data = data
        self.trade_id = data["id"]
        self.created = datetime.strptime(data["created"], "%Y-%m-%dT%H:%M:%S%zZ")
        self.status = data["status"]