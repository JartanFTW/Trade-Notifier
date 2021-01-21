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



from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import json

class ImageBuilder(Exception):

    def __init__(self, theme_folder_path: str, give_items: list, take_items: list, item_images: dict):

        self.theme_folder_path = theme_folder_path

        self.give_items = give_items

        self.take_items = take_items

        self.item_images = item_images

        self.images = {}

        self.fonts = {}



    def load_settings(self):

        with open(os.path.join(self.theme_folder_path, "theme_setup.json")) as settings:
            self.settings = json.load(settings)



    def load_background(self):

        self.background = Image.open(os.path.join(self.theme_folder_path, "background.png"))

    

    def load_images(self):

        for image_name, image_data in self.settings["drawn_images"]:
            self.images[image_name] = Image.open(os.path.join(self.theme_folder_path, image_data["file_name"]))
    


    def load_fonts(self):
        
        for text_name, text_data in self.settings["drawn_text"]:
            self.fonts[text_name] = ImageFont.truetype(os.path.join(self.theme_folder_path, text_data["font_file_name"]), text_data["font_size"])



    def stitch_give_item_images(self):

        for i in range(4):

            try:
                item_image = self.item_images[str(self.give_items[i]["id"])]
            except IndexError:
                break
            
            x = self.settings["give_items"][i][0] - (item_image.width / 2)
            y = self.settings["give_items"][i][1] + (item_image.height / 2)
            box = (int(round(x)), int(round(y)))

            self.background.paste(item_image, mask = item_image, box = box)



    def stitch_take_item_images(self):

        for i in range(4):

            try:
                item_image = self.item_images[str(self.take_items[i]["id"])]
            except IndexError:
                break
            
            x = self.settings["take_items"][i][0] - (item_image.width / 2)
            y = self.settings["take_items"][i][1] + (item_image.height / 2)
            box = (int(round(x)), int(round(y)))

            self.background.paste(item_image, mask = item_image, box = box)



    def stitch_images(self):

        for image_name, image_data in self.settings["drawn_images"]:

            image = self.images[image_name]

            mask = None
            if image["transparency"] == True:

                mask = self.images[image_name]
            
            box = tuple(image_data["top_left_position"])

            self.background.paste(image, mask = mask, box = box)



    def draw_text(self):

        draw = ImageDraw.Draw(self.background)

        for text_name, text_data in self.settings["drawn_text"]:

            box = tuple(text_data["top_left_position"])

            text = self.format_text(text_data["text"])

            font = self.fonts[text_name]

            fill = tuple(text_data["rgb"])

            draw.text(box, text, font = font, fill = fill)



    def format_text(self, text):

        give_rap = sum(item["rap"] for item in self.give_items)

        give_roli_value = sum(item["roli_value"] for item in self.give_items)

        take_rap = sum(item["rap"] for item in self.take_items)

        take_roli_value = sum(item["roli_value"] for item in self.take_items)

        text = text.format(
            give_rap = give_rap, 
            give_roli_value = give_roli_value, 
            take_rap = take_rap, 
            take_roli_value = take_roli_value
            )

        return text