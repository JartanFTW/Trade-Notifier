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
from io import BytesIO
import json
import os
from collections import OrderedDict

# Third Party
from PIL import Image, ImageDraw, ImageFont

# Local
from utilities import format_text


class NotificationBuilder(Exception):
    def __init__(self, theme_folder: str):
        self.theme_folder = theme_folder
        self.load_settings(theme_folder)
        pass

    def build_image(self, trade_data: dict):
        """Takes in trade data and builds notification according to theme_setup, in the order that it's written in theme_setup."""
        notification = self.load_image(
            os.path.join(self.theme_folder, self.settings["background_image"])
        )
        for section, details in self.settings.items():
            if section == "background_image":
                continue

            elif section in ("give", "take", "drawn_images"):
                for item_name, item_details in details.items():
                    background = notification

                    if section == "drawn_images":
                        foreground = self.load_image(
                            os.path.join(self.theme_folder, item_details["file_name"])
                        )
                    else:
                        try:
                            foreground = trade_data[section]["items"][item_name][
                                "pillowImage"
                            ]
                        except KeyError:  # Catching keyerror for trades that have less than 4 items on a side
                            continue

                    foreground = self.resize_image(
                        foreground, tuple(item_details["size"])
                    )

                    position = item_details["position"]

                    if item_details["center_on_position"]:
                        position[0] = int(
                            round(position[0] - (item_details["size"][0] / 2))
                        )
                        position[1] = int(
                            round(position[1] - (item_details["size"][1] / 2))
                        )
                    position = tuple(position)

                    transparency = item_details["transparency"]

                    self.stitch_images(
                        background, foreground, position, transparency=transparency
                    )
                    continue

            elif section == "drawn_text":
                for text_details in details.values():
                    background = notification
                    position = tuple(text_details["position"])
                    text = format_text(text_details["text"], trade_data=trade_data)
                    rgba = tuple(text_details["rgba"])
                    font = self.load_font(
                        os.path.join(self.theme_folder, text_details["font_file"]),
                        font_size=text_details["font_size"],
                    )

                    anchor = "la"
                    if text_details["center_on_position"]:
                        anchor = "mm"

                    stroke_rgba = tuple(text_details["stroke_rgba"])
                    stroke_width = text_details["stroke_width"]

                    background = self.stitch_text(
                        background,
                        position,
                        text,
                        rgba=rgba,
                        font=font,
                        anchor=anchor,
                        stroke_rgba=stroke_rgba,
                        stroke_width=stroke_width,
                    )
                    continue

            else:
                print(f"Unknown theme section: {section}")
                continue

        notification_bytes = BytesIO()
        notification.save(notification_bytes, "PNG")
        notification_bytes.seek(0)

        return notification_bytes

    def load_settings(self, theme_folder: str):
        """Loads a json file from the folder path provided + "theme_setup.json" into an OrderedDict as self.settings"""
        json_path = os.path.join(theme_folder, "theme_setup.json")
        with open(json_path) as config:
            self.settings = json.load(config, object_pairs_hook=OrderedDict)

    def load_font(self, font_path: str, font_size: int):
        """Loads a specified font from the path provided and returns the PIL ImageFont object"""
        font = ImageFont.truetype(font_path, font_size)
        return font

    def load_image(self, image_path: str):
        """Loads a specific image from the path provided, converts it to RGBA, and returns the PIL Image object"""
        image = Image.open(image_path).convert("RGBA")
        return image

    def stitch_images(
        self,
        background: Image,
        foreground: Image,
        top_left_position: tuple,
        transparency: bool = False,
    ):
        """Places PIL foreground onto PIL background at the top_left_position, passing foreground as the mask if transparency is True, and then returns the background"""
        if not transparency:
            mask = None
            alpha = foreground.convert("RGBA").split()[
                -1
            ]  # Getting alpha channel of foreground
            new_foreground = Image.new(
                "RGBA", foreground.size, (255, 255, 255, 255)
            )  # Creating image with white background
            new_foreground.paste(
                foreground, mask=alpha
            )  # Placing foreground on white background to remove all transparency
            foreground = new_foreground

        mask = foreground

        background.paste(foreground, box=top_left_position, mask=mask)

    def stitch_text(
        self,
        background: Image,
        position: tuple,
        text: str,
        rgba: tuple = None,
        font: ImageFont = None,
        anchor: str = "la",
        stroke_rgba: tuple = None,
        stroke_width: int = 0,
    ):
        """Pillow documentation explains it better than I could: https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html#PIL.ImageDraw.ImageDraw.text"""
        text_image = Image.new("RGBA", background.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_image)
        draw.text(
            position,
            text,
            fill=rgba,
            font=font,
            anchor=anchor,
            stroke_fill=stroke_rgba,
            stroke_width=stroke_width,
        )
        background.paste(text_image, mask=text_image)
        return background

    def resize_image(self, image: Image, size: tuple):
        """Resizes a pillow image and returns it"""
        resized_image = image.resize(size, resample=Image.LANCZOS)
        return resized_image