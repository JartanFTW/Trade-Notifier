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

# Third Party
from discord import Embed, Webhook
import httpx

# Local
from .discord import HttpxWebhookAdapter
from .errors import UnknownResponse
from .utils import format_print

log = logging.getLogger(__name__)


async def check_for_update(current_version: str) -> tuple[bool, str]:
    """Checks if provided current_version variable matches that of tag_name on the latest release GitHub API
    Returns a tuple containing:
    A bool which will be true if an update is available
    A string containing the latest version tag
    """
    log.debug("Checking for update")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/repos/JartanFTW/Trade-Notifier/releases/latest"
        )
    if resp.status_code == 200:
        log.debug("Checked for update")
        if current_version != resp.json()["tag_name"]:
            return (True, resp.json()["tag_name"])
        return (False, resp.json()["tag_name"])
    raise UnknownResponse(resp.response_code, resp.url, response_text=resp.text)


async def check_for_update_loop(
    current_version: str, delay: int = 60, webhook_url: str = None
):
    """Checks for an update every 60 minutes, and if it finds one sends an alert to the webhook provided."""
    while True:
        update = await check_for_update(current_version)
        if update[0]:
            format_print(f"Horizon update {update[1]} is available!", log_level=30)
            if webhook_url:
                async with httpx.AsyncClient() as client:
                    webhook = Webhook.from_url(
                        webhook_url, adapter=HttpxWebhookAdapter(client)
                    )
                    embed = Embed(
                        title=f"Horizon Update {update[1]} is available!",
                        description="A new update for Horizon means added features, stability, and an overall better experience.",
                        url="https://github.com/JartanFTW/Trade-Notifier/releases/latest",
                        color=16294974,
                    )
                    await webhook.send(embed=embed)
        await asyncio.sleep(delay * 60)
