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

log = logging.getLogger(__name__)


class UnknownResponse(Exception):
    def __init__(self, response_code: int, url: str, response_text: str = None):
        self.response_code = response_code
        self.url = url
        self.response_text = response_text
        self.err = (
            f"An unknown response code {response_code} was received when calling {url}"
        )
        log.error(self.err)
        super().__init__(self.err)


class InvalidCookie(Exception):
    def __init__(self, cookie: str, response_code: int = None, url: str = None):
        self.cookie = cookie
        self.response_code = response_code
        self.url = url
        self.err = f"An invalid roblosecurity cookie was detected with response code {response_code} when calling {url} cookie with cookie ending with {cookie[-5:]}"
        log.error(self.err)
        super().__init__(self.err)
