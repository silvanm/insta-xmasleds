#!/usr/bin/python3

"""
Version using json-files preprocessed in the directory "imagedata"
"""


import os
import time
from datetime import datetime, timedelta
from random import randint

import board
import neopixel
import json

import pytz
import requests
import dateparser

# Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
# NeoPixels must be connected to D10, D12, D18 or D21 to work.
pixel_pin = board.D18

# The number of NeoPixels
num_pixels = 600

# Ratio of height to width
height_to_width = 3

# The number of rows the both images overlap
OVERLAP_ROWS = 50

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRB

# Imagedata
images = []

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=1, auto_write=False,
                           pixel_order=ORDER)

# Switch to the current dir
os.chdir(os.path.dirname(os.path.realpath(__file__)))

def log(msg):
    print(msg)

def check_is_night_via_webservice():
    """
    Returns True if it's night.
    :return: boolean
    """
    r = requests.get('https://api.sunrise-sunset.org/json?lat=47.376888&lng=8.541694&formatted=0')
    if r.status_code==200:
        response = r.json()
        sunrise = dateparser.parse(response['results']['sunrise']) + timedelta(minutes=30)
        sunset = dateparser.parse(response['results']['sunset']) - timedelta(minutes=30)
        its_night = datetime.now(pytz.utc) < sunrise or datetime.now(pytz.utc) > sunset
        log("It's night? %s " % ('yes' if its_night else 'no') )
        return its_night
    else:
        log("Unknown sunrise/sunset")
        return None


def load_images():
    for filename in sorted(os.listdir("imagedata")):
        with open(os.path.join("imagedata", filename), 'r') as file:
            log("Loading %s " % filename)
            images.append(json.load(file))


def prevent_darkness(tuple):
    """ Makes sure that the RGB values are never (0,0,0) to prevent too much contrast """
    return [1 if v == 0 else v for v in tuple]


def get_row_using_crossfade(image_index, y):
    """ Returns the current row considering crossfade effects.
    :param image_index: Current active image
    :param y: Current row number
    :return: all color values for one row
    """
    row = images[image_index][y]
    # print("imag_index=%d, pos=%d" % (image_index, y), end="\r")
    if y >= OVERLAP_ROWS:
        # no overlap
        pass
    else:
        # has overlap
        prev_picture = images[(image_index + len(images) - 1) % len(images)]
        for x in range(0, num_pixels):
            for channel in range(0, 3):
                row[x][channel] = int((1- y / OVERLAP_ROWS) * prev_picture[num_pixels  * height_to_width - OVERLAP_ROWS + y][x][channel]) \
                                  + int((y / OVERLAP_ROWS) * images[image_index][y][x][channel])

                assert row[x][channel] >= 0 and row[x][channel] < 256
    return row


def display_image():
    # Start with a random image
    current_image_index = randint(0, len(images))
    lights_on = True
    while True:
        if current_image_index == 0:
            is_night = check_is_night_via_webservice()
            if is_night is not None:
                lights_on = is_night

            if datetime.now().hour < 6:
                log("turn off between 0 AM and 6 AM")
                lights_on = False

        log("Current image index: %d" % current_image_index)
        for y in range(0, num_pixels * height_to_width - OVERLAP_ROWS):
            row = get_row_using_crossfade(current_image_index, y)
            for index, val in enumerate(row):
                if index < num_pixels:
                    if lights_on:
                        pixels[index] = tuple(prevent_darkness(val))
                    else:
                        pixels[index] = (0,0,0)
            pixels.show()
            time.sleep(0.02)
        current_image_index = (current_image_index + 1) % len(images)


def test():
    for i in range(0, 255):
        for x in range(0, num_pixels):
            pixels[x] = (0, 0, i)

        print(i)
        pixels.show()
        time.sleep(0.5)

check_is_night_via_webservice()
load_images()
display_image()
