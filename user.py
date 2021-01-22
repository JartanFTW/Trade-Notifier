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
import asyncio
import logging
from utilities import UnknownResponse, InvalidCookie
import sys

logger = logging.getLogger("horizon.user")


class User():

    @classmethod # Factory method to allow for async initialization function calls
    async def create(cls, security_cookie):

        self = User()

        self.client = httpx.AsyncClient(cookies={})

        self.client.cookies[".ROBLOSECURITY"] = security_cookie

        await self.update_csrf()

        await self.update_id()

        return self



    async def update_csrf(self):

        while True:

            logger.info("Updating user csrf token")

            request = await self.client.post("https://auth.roblox.com/v1/logout")

            try:

                self.client.cookies["X-CSRF-TOKEN"] = request.headers["x-csrf-token"]

                logger.debug(f"Updated user csrf token: {request.headers['x-csrf-token']}")

                return
            
            except KeyError:

                logger.warning(f"Failed to update user csrf token: {request.status_code}")

                if request.status_code == 429:
                    
                    await asyncio.sleep(5)

                    continue

                elif request.status_code == 401:

                    logger.critical("Cookie is invalid")
                    
                    raise InvalidCookie(request.status_code, request.url, response_text = request.text)
            
                else:

                    logger.critical(f"Encountered an unknown response code while updating user csrf: {request.status_code}")

                    raise UnknownResponse(request.status_code, request.url, response_text = request.text)



    async def update_id(self):

        attempt = 0

        while True:

            logger.info("Updating user id")

            request = await self.client.get("https://www.roblox.com/game/GetCurrentUser.ashx")

            if request.status_code == 200 and request.text != "null":

                self.id = int(request.text)

                logger.debug(f"Updated user id: {request.text}")

                return
            
            logger.warning(f"Failed to update user id: {request.status_code}")

            if request.status_code == 429:

                await asyncio.sleep(5)

                continue

            else:

                attempt += 1
                
                if attempt > 2:
                    
                    logger.critical(f"Unable to update user id: {request.status_code}")

                    raise UnknownResponse(request.status_code, request.url, response_text = request.text)

                logger.error(f"Unable to update user id: {request.status_code}")
                
                await self.update_csrf()

                continue



    async def get_trade_status_data(self, tradeStatusType: str = "Inbound", limit: int = 10, sortOrder: str = "Asc"):

        attempt = 0

        while True:

            logger.info("Grabbing user trade status data")

            request = await self.client.get(f"https://trades.roblox.com/v1/trades/{tradeStatusType}?limit={limit}&sortOrder={sortOrder}")

            if request.status_code == 200:

                request_json = request.json()

                logger.debug(f"Grabbed user trade status data: {request_json}")

                return request_json

            logger.warning(f"Failed to grab user trade status data: {request.status_code}")

            if request.status_code == 429:

                await asyncio.sleep(5)

                continue

            else:

                attempt += 1

                if attempt > 2:

                    logger.critical(f"Unable to grab user trade status data: {request.status_code}")

                    raise UnknownResponse(request.status_code, request.url, response_text = request.text)
                
                logger.error(f"Unable to grab user trade status data: {request.status_code}")

                await self.update_csrf

                continue



    async def get_trade_data(self, trade_id: [str, int]):

        attempt = 0

        while True:

            logger.info("Grabbing user trade data")

            request = await self.client.get(f"https://trades.roblox.com/v1/trades/{trade_id}")

            if request.status_code == 200:

                request_json = request.json()

                logger.debug(f"Grabbed user trade data: {request_json}")

                return request_json

            logger.warning(f"Failed to grab user trade data: {request.status_code}")

            if request.status_code == 429:

                await asyncio.sleep(5)

                continue
            
            else:

                attempt += 1

                if attempt > 2:

                    logger.critical(f"Unable to grab user trade data: {request.status_code}")

                    raise UnknownResponse(request.status_code, request.url, response_text = request.text)
                
                logger.error(f"Unable to grab user trade data: {request.status_code}")

                await self.update_csrf

                continue