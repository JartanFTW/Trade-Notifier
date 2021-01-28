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



from io import BytesIO
import os
import json
from collections import OrderedDict
from PIL import Image, ImageDraw, ImageFont
import traceback

class NotificationBuilder(Exception):
    
    def __init__(self, theme_folder: str):
        self.theme_folder = theme_folder
        self.load_settings(theme_folder)
        pass
        #TODO Add check to see if all required files by config are present.

    def build_image(self, trade_data: dict):
        """Takes in trade data and builds notification according to theme_setup, in the order that it's written in theme_setup.
        """
        notification = self.load_image(os.path.join(self.theme_folder, self.settings['background_image']))
        for section, details in self.settings.items():
            if section == "background_image":
                continue

            elif section in ("give", "take", "drawn_images"):
                for item_name, item_details in details.items():
                    background = notification

                    if section == "drawn_images":
                        foreground = self.load_image(os.path.join(self.theme_folder, item_details['file_name']))
                    else:
                        try:
                            foreground = trade_data[section]['items'][item_name]['pillowImage']
                        except KeyError: # Catching keyerror for trades that have less than 4 items on a side
                            continue

                    foreground = self.resize_image(foreground, tuple(item_details['size']))

                    position = item_details['position']

                    if item_details['center_on_position']:
                        position[0] = int(round(position[0] - (item_details['size'][0]/2)))
                        position[1] = int(round(position[1] - (item_details['size'][1]/2)))
                    position = tuple(position)
                    
                    transparency = item_details['transparency']
                    
                    self.stitch_images(background, foreground, position, transparency=transparency)
                    continue

            elif section == "drawn_text":
                for text_details in details.values():
                    background = notification
                    position = tuple(text_details['position'])
                    try:
                        text = self.format_text(text_details['text'], trade_data=trade_data)
                    except Exception:
                        traceback.print_exc()
                    rgba = tuple(text_details['rgba'])
                    font = self.load_font(os.path.join(self.theme_folder, text_details['font_file']), font_size=text_details['font_size'])
                    
                    anchor = "la"
                    if text_details['center_on_position']:
                        anchor = "mm"
                    
                    stroke_rgba = tuple(text_details['stroke_rgba'])
                    stroke_width = text_details['stroke_width']

                    background = self.stitch_text(background, position, text, rgba=rgba, font=font, anchor=anchor, stroke_rgba=stroke_rgba, stroke_width=stroke_width)
                    continue

            else:
                print(f"Unknown theme section: {section}")
                continue
        
        notification_bytes = BytesIO()
        notification.save(notification_bytes, "PNG")
        notification_bytes.seek(0)

        return notification_bytes

    def load_settings(self, theme_folder: str):
        """Loads a json file from the folder path provided + "theme_setup.json" into an OrderedDict as self.settings
        """
        json_path = os.path.join(theme_folder, "theme_setup.json")
        with open(json_path) as config:
            self.settings = json.load(config, object_pairs_hook = OrderedDict)
    
    def load_font(self, font_path: str, font_size: int):
        """Loads a specified font from the path provided and returns the PIL ImageFont object
        """
        font = ImageFont.truetype(font_path, font_size)
        return font
    
    def load_image(self, image_path: str):
        """Loads a specific image from the path provided, converts it to RGBA, and returns the PIL Image object
        """
        image = Image.open(image_path).convert("RGBA")
        return image
    
    def stitch_images(self, background: Image, foreground: Image, top_left_position: tuple, transparency: bool = False):
        """Places PIL foreground onto PIL background at the top_left_position, passing foreground as the mask if transparency is True, and then returns the background
        """
        if not transparency:
            mask = None
            alpha = foreground.convert("RGBA").split()[-1] # Getting alpha channel of foreground
            new_foreground = Image.new("RGBA", foreground.size, (255,255,255,255)) # Creating image with white background
            new_foreground.paste(foreground, mask=alpha) # Placing foreground on white background to remove all transparency
            foreground = new_foreground
        
        mask = foreground

        background.paste(foreground, box=top_left_position, mask=mask)
    
    def stitch_text(self, background: Image, position: tuple, text: str, rgba: tuple = None, font: ImageFont = None, anchor: str = "la", stroke_rgba: tuple = None, stroke_width: int = 0):
        """Pillow documentation explains it better than I could: https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html#PIL.ImageDraw.ImageDraw.text
        """
        text_image = Image.new("RGBA", background.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_image)
        draw.text(position, text, fill=rgba, font=font, anchor=anchor, stroke_fill=stroke_rgba, stroke_width=stroke_width)
        background.paste(text_image, mask=text_image)
        return background
    
    def resize_image(self, image: Image, size: tuple):
        """Resizes a pillow image and returns it
        """
        resized_image = image.resize(size, resample=Image.LANCZOS)
        return resized_image
    
    def format_text(self, text: str, trade_data: dict): #TODO ADD UNVALUED RAPS TO VALUE
        """Formats different keywords for text stitching"""
        give_rap = sum(int(item['recentAveragePrice']) for item in trade_data['give']['items'].values())
        take_rap = sum(int(item['recentAveragePrice']) for item in trade_data['take']['items'].values())
        
        give_roli_value = sum(int(item['roliValue']) for item in trade_data['give']['items'].values())
        take_roli_value = sum(int(item['roliValue']) for item in trade_data['take']['items'].values())
        if trade_data['addUnvaluedToValue']:
            give_roli_value += sum(item['recentAveragePrice'] for item in trade_data['give']['items'].values() if item['roliValue'] == 0)
            take_roli_value += sum(item['recentAveragePrice'] for item in trade_data['take']['items'].values() if item['roliValue'] == 0)
        
        give_robux = str(trade_data['give']['robux'])
        take_robux = str(trade_data['take']['robux'])
        
        give_user_id = str(trade_data['give']['user']['id'])
        take_user_id = str(trade_data['take']['user']['id'])
        give_user_name = trade_data['give']['user']['name']
        take_user_name = trade_data['take']['user']['name']
        give_user_display_name = trade_data['give']['user']['displayName']
        take_user_display_name = trade_data['take']['user']['displayName']

        trade_status = "Inbound" if trade_data['status'] == "Open" else trade_data['status']

        item_filter = ["item2", "item3", "item4"]
        var_filter = ["id", "serialNumber", "assetId", "name", "originalPrice", "assetStock"]
        for side in ("give", "take"):
            for item in trade_data[side]['items']:
                for key, value in trade_data[side]['items'][item].items(): # Changing NoneTypes to empty strings so they show up as nothing on notification.
                    if value == None:
                        trade_data[side]['items'][item][key] = ""
            for x in item_filter: # Adding all items to dict so .format below doesn't scream IndexError. Can't just try/except it because then it won't work. If anyone has a better solution be my guest.
                if x not in trade_data[side]['items']:
                    trade_data[side]['items'][x] = {}
            for item in trade_data[side]['items'].values(): # Making sure all used indexes are in items for above reason.
                for x in var_filter:
                    if x not in item:
                        item[x] = ""
                for x in ["recentAveragePrice", "roliValue"]: # Same as above, but setting to 0 so total calculations don't scream.
                    if x not in item:
                        item[x] = 0
    

        text = text.format(
            give_rap = give_rap,
            take_rap = take_rap,
            give_roli_value = give_roli_value,
            take_roli_value = take_roli_value,
            give_robux = give_robux,
            take_robux = take_robux,
            give_user_id = give_user_id,
            take_user_id = take_user_id,
            give_user_name = give_user_name,
            take_user_name = take_user_name,
            give_user_display_name = give_user_display_name,
            take_user_display_name = take_user_display_name,
            trade_status = trade_status,
            give_item1_id = str(trade_data['give']['items']['item1']['id']),
            give_item2_id = str(trade_data['give']['items']['item2']['id']),
            give_item3_id = str(trade_data['give']['items']['item3']['id']),
            give_item4_id = str(trade_data['give']['items']['item4']['id']),
            take_item1_id = str(trade_data['take']['items']['item1']['id']),
            take_item2_id = str(trade_data['take']['items']['item2']['id']),
            take_item3_id = str(trade_data['take']['items']['item3']['id']),
            take_item4_id = str(trade_data['take']['items']['item4']['id']),
            give_item1_serialNumber = str(trade_data['give']['items']['item1']['serialNumber']),
            give_item2_serialNumber = str(trade_data['give']['items']['item2']['serialNumber']),
            give_item3_serialNumber = str(trade_data['give']['items']['item3']['serialNumber']),
            give_item4_serialNumber = str(trade_data['give']['items']['item4']['serialNumber']),
            take_item1_serialNumber = str(trade_data['take']['items']['item1']['serialNumber']),
            take_item2_serialNumber = str(trade_data['take']['items']['item2']['serialNumber']),
            take_item3_serialNumber = str(trade_data['take']['items']['item3']['serialNumber']),
            take_item4_serialNumber = str(trade_data['take']['items']['item4']['serialNumber']),
            give_item1_asset_id = str(trade_data['give']['items']['item1']['assetId']),
            give_item2_asset_id = str(trade_data['give']['items']['item2']['assetId']),
            give_item3_asset_id = str(trade_data['give']['items']['item3']['assetId']),
            give_item4_asset_id = str(trade_data['give']['items']['item4']['assetId']),
            take_item1_asset_id = str(trade_data['take']['items']['item1']['assetId']),
            take_item2_asset_id = str(trade_data['take']['items']['item2']['assetId']),
            take_item3_asset_id = str(trade_data['take']['items']['item3']['assetId']),
            take_item4_asset_id = str(trade_data['take']['items']['item4']['assetId']),
            give_item1_name = trade_data['give']['items']['item1']['name'],
            give_item2_name = trade_data['give']['items']['item2']['name'],
            give_item3_name = trade_data['give']['items']['item3']['name'],
            give_item4_name = trade_data['give']['items']['item4']['name'],
            take_item1_name = trade_data['take']['items']['item1']['name'],
            take_item2_name = trade_data['take']['items']['item2']['name'],
            take_item3_name = trade_data['take']['items']['item3']['name'],
            take_item4_name = trade_data['take']['items']['item4']['name'],
            give_item1_recent_average_price = str(trade_data['give']['items']['item1']['recentAveragePrice']),
            give_item2_recent_average_price = str(trade_data['give']['items']['item2']['recentAveragePrice']),
            give_item3_recent_average_price = str(trade_data['give']['items']['item3']['recentAveragePrice']),
            give_item4_recent_average_price = str(trade_data['give']['items']['item4']['recentAveragePrice']),
            take_item1_recent_average_price = str(trade_data['take']['items']['item1']['recentAveragePrice']),
            take_item2_recent_average_price = str(trade_data['take']['items']['item2']['recentAveragePrice']),
            take_item3_recent_average_price = str(trade_data['take']['items']['item3']['recentAveragePrice']),
            take_item4_recent_average_price = str(trade_data['take']['items']['item4']['recentAveragePrice']),
            give_item1_original_price = str(trade_data['give']['items']['item1']['originalPrice']),
            give_item2_original_price = str(trade_data['give']['items']['item2']['originalPrice']),
            give_item3_original_price = str(trade_data['give']['items']['item3']['originalPrice']),
            give_item4_original_price = str(trade_data['give']['items']['item4']['originalPrice']),
            take_item1_original_price = str(trade_data['take']['items']['item1']['originalPrice']),
            take_item2_original_price = str(trade_data['take']['items']['item2']['originalPrice']),
            take_item3_original_price = str(trade_data['take']['items']['item3']['originalPrice']),
            take_item4_original_price = str(trade_data['take']['items']['item4']['originalPrice']),
            give_item1_asset_stock = str(trade_data['give']['items']['item1']['assetStock']),
            give_item2_asset_stock = str(trade_data['give']['items']['item2']['assetStock']),
            give_item3_asset_stock = str(trade_data['give']['items']['item3']['assetStock']),
            give_item4_asset_stock = str(trade_data['give']['items']['item4']['assetStock']),
            take_item1_asset_stock = str(trade_data['take']['items']['item1']['assetStock']),
            take_item2_asset_stock = str(trade_data['take']['items']['item2']['assetStock']),
            take_item3_asset_stock = str(trade_data['take']['items']['item3']['assetStock']),
            take_item4_asset_stock = str(trade_data['take']['items']['item4']['assetStock']),
            give_item1_roli_value = str(trade_data['give']['items']['item1']['roliValue']),
            give_item2_roli_value = str(trade_data['give']['items']['item2']['roliValue']),
            give_item3_roli_value = str(trade_data['give']['items']['item3']['roliValue']),
            give_item4_roli_value = str(trade_data['give']['items']['item4']['roliValue']),
            take_item1_roli_value = str(trade_data['take']['items']['item1']['roliValue']),
            take_item2_roli_value = str(trade_data['take']['items']['item2']['roliValue']),
            take_item3_roli_value = str(trade_data['take']['items']['item3']['roliValue']),
            take_item4_roli_value = str(trade_data['take']['items']['item4']['roliValue'])
            )

        return text