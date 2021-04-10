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
import sys
import traceback

# Third Party
import httpx

# Local
from trade_worker import TradeWorker
from user import User
from utilities import (
    load_config,
    setup_logging,
    print_timestamp,
    check_for_update_loop,
    InvalidCookie,
)

version = "v0.3.3-alpha"
os.system("title " + f"Horizon {version}")

logger = logging.getLogger("horizon.main")


async def main():

    if getattr(sys, "frozen", False):  # Check if program is compiled to exe
        main_folder_path = os.path.dirname(sys.executable)
    else:
        main_folder_path = os.path.dirname(os.path.abspath(__file__))

    config = load_config(os.path.join(main_folder_path, "horizon_config.ini"))
    setup_logging(main_folder_path, level=config["logging_level"])

    print_timestamp(
        f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW"
    )
    logger.log(
        49,
        f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW",
    )

    users = []
    tasks = []
    for cookie in config["cookies"]:
        try:
            user = await User.create(cookie)
            users.append(user)
        except InvalidCookie:
            print_timestamp(f"An invalid cookie was detected: {cookie}")
            continue
        if config["completed"]["enabled"]:
            worker = await TradeWorker.create(
                main_folder_path,
                user,
                config["completed"]["webhook"],
                config["completed"]["update_interval"],
                config["completed"]["theme_name"],
                trade_type="Completed",
                add_unvalued_to_value=config["add_unvalued_to_value"],
                testing=config["testing"],
                webhook_content=config["completed"]["webhook_content"],
            )
            tasks.append(asyncio.create_task(worker.check_trade_loop()))
        if config["inbound"]["enabled"]:
            worker = await TradeWorker.create(
                main_folder_path,
                user,
                config["inbound"]["webhook"],
                config["inbound"]["update_interval"],
                config["inbound"]["theme_name"],
                trade_type="Inbound",
                add_unvalued_to_value=config["add_unvalued_to_value"],
                testing=config["testing"],
                double_check=config["double_check"],
                webhook_content=config["inbound"]["webhook_content"],
            )
            tasks.append(asyncio.create_task(worker.check_trade_loop()))
        if config["outbound"]["enabled"]:
            worker = await TradeWorker.create(
                main_folder_path,
                user,
                config["outbound"]["webhook"],
                config["outbound"]["update_interval"],
                config["outbound"]["theme_name"],
                trade_type="Outbound",
                add_unvalued_to_value=config["add_unvalued_to_value"],
                testing=config["testing"],
                webhook_content=config["outbound"]["webhook_content"],
            )
            tasks.append(asyncio.create_task(worker.check_trade_loop()))

    if tasks:
        if config["check_for_update"]:
            if config["completed"]["enabled"]:
                webhook_url = config["completed"]["webhook"]
            elif config["inbound"]["enabled"]:
                webhook_url = config["inbound"]["webhook"]
            else:
                webhook_url = config["outbound"]["webhook"]
            tasks.append(
                asyncio.create_task(check_for_update_loop(version, webhook_url))
            )
        await asyncio.wait(tasks)
    else:
        if not users:
            print_timestamp("All cookies are invalid! There is nothing for me to do :(")
        else:
            print_timestamp(
                "Looks like you don't have any trade types enabled in the config! There is nothing for me to do :("
            )
    for user in users:
        await user.client.aclose()
    return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logger.critical(f"An unknown critical error occurred: {traceback.format_exc()}")
        print(f"An unknown critical error occurred: {traceback.format_exc()}")
        print(
            "If you're seeing this, chances are something has gone horribly wrong.\nYou can read the above few lines to get an idea of what error has occurred.\nIf you don't know how to fix the issue, you should open an Issue in the GitHub and provide your latest log file from the logs folder.\nIf you don't have a GitHub, please provide the log file in the Horizon discord server."
        )
    finally:
        input("Operations have complete. Press Enter to exit.")