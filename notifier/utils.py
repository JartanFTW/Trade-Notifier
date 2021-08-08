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
from configparser import ConfigParser, SectionProxy
import logging
import os
import time

log = logging.getLogger(__name__)


def format_print(text: str, log_level: int = None) -> None:
    """Prints to console the provided string with a H:M:S | timestamp before it
    If log_level is provided it will also log the text without formatting, at the provided level."""
    formatted_text = time.strftime("%H:%M:%S | ", time.localtime()) + text
    print(formatted_text)
    if isinstance(log_level, int):
        log.log(log_level, text)


def load_config(path: str) -> dict:
    """Loads config from path provided and returns it formatted as a dict"""
    parser = ConfigParser()
    parser.read(path)

    def wrap_to_dict(to_wrap):
        wrapped = dict(to_wrap)
        for key, value in wrapped.items():
            if isinstance(value, ConfigParser) or isinstance(value, SectionProxy):
                wrapped[key] = wrap_to_dict(value)
            elif value.upper().strip() in ("TRUE", "FALSE"):
                wrapped[key] = True if value.upper().strip() == "TRUE" else False
            else:
                try:
                    wrapped[key] = int(value)
                except ValueError:
                    pass
        return wrapped

    config = wrap_to_dict(parser)
    return config
