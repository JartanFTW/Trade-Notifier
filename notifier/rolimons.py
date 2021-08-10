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
import logging

# Third Party
import httpx

# Local
from .errors import UnknownResponse

log = logging.getLogger(__name__)


async def get_rolimons_itemdetails() -> dict:
    """Fetches rolimons itemdetails data and returns it formatted as a dict"""
    log.debug("Fetching rolimons' itemdetails data")
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://www.rolimons.com/itemapi/itemdetails")
    if resp.status_code == 200:
        log.debug("Fetched rolimons' itemdetails data")
        return resp.json()
    raise UnknownResponse(resp.status_code, resp.url, response_text=resp.text)
