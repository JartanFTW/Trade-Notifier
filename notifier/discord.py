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
from discord import DiscordServerError, utils, webhook
from httpx import AsyncClient

log = logging.getLogger(__name__)


class HttpxWebhookAdapter(
    webhook.WebhookAdapter
):  # Adapted from discord.py AsyncWebhookAdapter to suit httpx & Horizon's needs. All credit to original author(s).
    """A webhook adapter suited for use with httpx.
    .. note::
        You are responsible for cleaning up the client session.
    Parameters
    -----------
    session: :class:`httpx.AsyncClient`
        The session to use to send requests.
    """

    def __init__(self, session: AsyncClient):
        self.session = session
        self.loop = asyncio.get_event_loop()

    def is_async(self):
        return True

    async def request(
        self, verb, url, payload=None, multipart=None, *, files=None, reason=None
    ):
        headers = {}
        data = None
        files = files or []
        if payload:
            headers["Content-Type"] = "application/json"
            data = utils.to_json(payload)

        if reason:
            headers["X-Audit-Log-Reason"] = self._uriquote(reason, safe="/ ")

        base_url = url.replace(self._request_url, "/") or "/"
        _id = self._webhook_id
        for tries in range(5):
            for file in files:
                file.reset(seek=tries)

            attachments = None
            if multipart:
                data = {}
                attachments = {}
                for key, value in multipart.items():
                    if key.startswith("file"):
                        attachments[key] = (value[0], value[1], "multipart/form-data")
                    else:
                        data[key] = value

            r = await self.session.request(
                verb, url, headers=headers, data=data, files=attachments
            )
            r.status = r.status_code
            r.reason = r.reason_phrase
            log.debug(
                "Webhook ID %s with %s %s has returned status code %s",
                _id,
                verb,
                base_url,
                r.status_code,
            )
            # Coerce empty strings to return None for hygiene purposes
            response = (r.text) or None
            if r.headers["Content-Type"] == "application/json":
                response = r.json()

            # check if we have rate limit header information
            remaining = r.headers.get("X-Ratelimit-Remaining")
            if remaining == "0" and r.status != 429:
                delta = utils._parse_ratelimit_header(r)
                log.debug(
                    "Webhook ID %s has been pre-emptively rate limited, waiting %.2f seconds",
                    _id,
                    delta,
                )
                await asyncio.sleep(delta)

            if 300 > r.status_code >= 200:
                return response

            # we are being rate limited
            if r.status_code == 429:
                if not r.headers.get("Via"):
                    # Banned by Cloudflare more than likely.
                    raise webhook.HTTPException(r, data)

                retry_after = response["retry_after"] / 1000.0
                log.warning(
                    "Webhook ID %s is rate limited. Retrying in %.2f seconds",
                    _id,
                    retry_after,
                )
                await asyncio.sleep(retry_after)
                continue

            if r.status_code in (500, 502):
                await asyncio.sleep(1 + tries * 2)
                continue

            if r.status_code == 403:
                raise webhook.Forbidden(r, response)
            elif r.status_code == 404:
                raise webhook.NotFound(r, response)
            else:
                raise webhook.HTTPException(r, response)

        # no more retries
        if r.status >= 500:
            raise DiscordServerError(r, response)
        raise webhook.HTTPException(r, response)

    async def handle_execution_response(self, response, *, wait):
        data = await response
        if not wait:
            return data

        # transform into Message object
        # Make sure to coerce the state to the partial one to allow message edits/delete
        state = webhook._PartialWebhookState(
            self, self.webhook, parent=self.webhook._state
        )
        return webhook.WebhookMessage(
            data=data, state=state, channel=self.webhook.channel
        )
