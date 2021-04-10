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

# Third-Party
import httpx

# Local
from utilities import UnknownResponse, InvalidCookie

logger = logging.getLogger("horizon.user")


class User:
    @classmethod
    async def create(cls, security_cookie):
        """Factory method to allow for async initialization of User object.
        security_cookie should be formatted as: "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_xyz123"
        Returns a User() object with a loaded up csrf token and id.
        """
        logger.debug("Creating user object")
        self = User()
        self.client = httpx.AsyncClient(cookies={})
        self.client.cookies[".ROBLOSECURITY"] = security_cookie
        try:
            await self.update_csrf()
        except InvalidCookie as e:
            await self.client.aclose()
            raise (e)
        await self.update_user_info()
        logger.info("Created user object")
        return self

    async def update_csrf(self):
        """Updates the self.client x-csrf-token cookie (in reality is a header but passed in as a cookie to roblox works)
        Returns None
        """
        while True:
            logger.debug("Updating user x-csrf-token")
            request = await self.client.post("https://auth.roblox.com/v1/logout")
            try:
                self.client.cookies["X-CSRF-TOKEN"] = request.headers["x-csrf-token"]
                logger.info("Updated user x-csrf-token")
                return
            except KeyError:
                if request.status_code == 429:
                    await asyncio.sleep(5)
                    continue
                if request.status_code == 401:
                    raise InvalidCookie(
                        request.status_code,
                        request.url,
                        response_text=request.text,
                        cookie=self.client.cookies[".ROBLOSECURITY"],
                    )
                else:
                    raise UnknownResponse(
                        request.status_code, request.url, response_text=request.text
                    )

    async def update_user_info(self):
        """Updates self.id to integer id of roblox account tied to the security_cookie passed in on class creation.
        Returns None
        """
        while True:
            logger.debug("Updating user info")
            request = await self.client.get(
                "https://users.roblox.com/v1/users/authenticated"
            )
            if request.status_code == 200:
                request_json = request.json()
                self.id = int(request_json["id"])
                self.name = request_json["name"]
                self.display_name = request_json["displayName"]
                logger.info("Updated user info")
                return
            elif request.status_code == 429:
                await asyncio.sleep(5)
                continue
            else:
                raise UnknownResponse(
                    request.status_code, request.url, response_text=request.text
                )

    async def get_trade_status_info(
        self, tradeStatusType: str = "Inbound", limit: int = 10, sortOrder: str = "Asc"
    ):
        """Grabs general details about a certain trade type.
        tradeStatusType can be Inbound, Outbound, or Completed
        limit can be 10, 25, or 100 as per Roblox API
        sortOrder can be Asc or Desc, but it seems to make no difference
        Returns a dict:
        {
        "previousPageCursor": "string",
        "nextPageCursor": "string",
        "data": [
            {
            "id": 0,
            "user": {
                "id": 0,
                "name": "string",
                "displayName": "string"
            },
            "created": "2021-03-17T02:56:19.557Z",
            "expiration": "2021-03-17T02:56:19.558Z",
            "isActive": true,
            "status": "Unknown"
            }
        ]
        }
        """
        attempt = 0
        while True:
            logger.debug(f"Grabbing user trade status info {tradeStatusType}")
            request = await self.client.get(
                f"https://trades.roblox.com/v1/trades/{tradeStatusType}?limit={limit}&sortOrder={sortOrder}"
            )
            if request.status_code == 200:
                request_json = request.json()
                logger.debug(f"Grabbed user trade status info {tradeStatusType}")
                return request_json
            if request.status_code == 429:
                await asyncio.sleep(5)
                continue
            else:
                attempt += 1
                if attempt > 2:
                    raise UnknownResponse(
                        request.status_code, request.url, response_text=request.text
                    )
                else:
                    await self.update_csrf()
                    continue

    async def get_trade_info(self, trade_id: int):
        """Grabs details about a specific trade id
        trade_id must be an integer id of a trade the account the class is tied to has access to
        Returns a dict:
        {
        "offers": [
            {
            "user": {
                "id": 0,
                "name": "string",
                "displayName": "string"
            },
            "userAssets": [
                {
                "id": 0,
                "serialNumber": 0,
                "assetId": 0,
                "name": "string",
                "recentAveragePrice": 0,
                "originalPrice": 0,
                "assetStock": 0,
                "membershipType": "None"
                }
            ],
            "robux": 0
            }
        ],
        "id": 0,
        "user": {
            "id": 0,
            "name": "string",
            "displayName": "string"
        },
        "created": "2021-03-17T02:56:19.540Z",
        "expiration": "2021-03-17T02:56:19.540Z",
        "isActive": true,
        "status": "Unknown"
        }
        """
        attempt = 0
        while True:
            logger.debug("Grabbing user trade info")
            request = await self.client.get(
                f"https://trades.roblox.com/v1/trades/{trade_id}"
            )
            if request.status_code == 200:
                request_json = request.json()
                logger.debug(f"Grabbed user trade info {trade_id}")
                return request_json
            if request.status_code == 429:
                await asyncio.sleep(5)
                continue
            else:
                attempt += 1
                if attempt > 2:
                    raise UnknownResponse(
                        request.status_code, request.url, response_text=request.text
                    )
                else:
                    await self.update_csrf()
                    continue