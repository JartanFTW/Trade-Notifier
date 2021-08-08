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
import time

log = logging.getLogger(__name__)


def format_print(text: str, log_level: int = None):
    """Prints to console the provided string with a H:M:S | timestamp before it
    If log_level is provided it will also log the text without formatting, at the provided level."""
    formatted_text = time.strftime("%H:%M:%S | ", time.localtime()) + text
    print(formatted_text)
    if isinstance(log_level, int):
        log.log(log_level, text)
