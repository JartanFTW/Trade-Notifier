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


import asyncio
import logging
import os
import sys
import traceback
import httpx
from trade_worker import TradeWorker
from user import User
from utilities import load_config, setup_logging, print_timestamp

version = "v0.3.1-alpha"
os.system("title " + f"Horizon {version}")

logger = logging.getLogger("horizon.main")


async def main():

    if getattr(sys, "frozen", False): # Check if program is compiled to exe
        main_folder_path = os.path.dirname(sys.executable)
    else:
        main_folder_path = os.path.dirname(os.path.abspath(__file__))

    config = load_config(os.path.join(main_folder_path, "horizon_config.ini"))
    setup_logging(main_folder_path, level = config['logging_level'])

    print_timestamp(f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW")
    logging.info(f"Horizon Trade Notifier {version} - https://discord.gg/Xu8pqDWmgE - https://github.com/JartanFTW")

    tasks = []
    user = await User.create(config["cookie"])
    if config['completed']['enabled']:
        worker = await TradeWorker.create(main_folder_path, user, config['webhook'], config['completed']['update_interval'], config['completed']['theme_name'], trade_type="Completed", add_unvalued_to_value=config['add_unvalued_to_value'], testing=config['testing'], webhook_content=config['completed']['webhook_content'])
        tasks.append(asyncio.create_task(worker.check_trade_loop()))
    if config['inbound']['enabled']:
        worker = await TradeWorker.create(main_folder_path, user, config['webhook'], config['inbound']['update_interval'], config['inbound']['theme_name'], trade_type="Inbound", add_unvalued_to_value=config['add_unvalued_to_value'], testing=config['testing'], webhook_content=config['inbound']['webhook_content'])
        tasks.append(asyncio.create_task(worker.check_trade_loop()))

    if tasks:
        await asyncio.wait(tasks)
    else:
        print_timestamp("Looks like you don't have any trade types enabled in the config! There is nothing for me to do :(")
    await user.client.aclose()
    return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.critical(f"An unknown critical error occurred: {traceback.format_exc()}")
        print(f"An unknown critical error occurred: {traceback.format_exc()}")
    finally:
        input("Operations have complete. Press Enter to exit.")