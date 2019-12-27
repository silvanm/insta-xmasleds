#!/usr/bin/python3

"""
Version fetching images directly via Instagram (using the proxy at
http://instagram-images-silvan-privat.appuioapp.ch/fetch?url=https://www.instagram.com/explore/tags/christmas/
"""

import os
import time
from datetime import datetime, timedelta
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from io import BytesIO
from collections import deque
import platform
import pytz
import requests
import dateparser
import time
import json
from math import floor, ceil, sin, cos, pi

# The number of NeoPixels
NUM_PIXELS = 780

# The number of Pixels to have black at the beginning
BLACK_OFFSET = 170

ANIMATION_DELAY = 0

# Ratio of height to width
HEIGHT_TO_WIDTH = 3

BLUR_PIXELS = 2

# Reduce saturation. 1 = no reduction
COLOR_LEVEL = 1

# The number of rows the both images overlap
OVERLAP_ROWS = 50

# Max illumination
MAX_LEVEL = 100

# Imagedata
images = deque()

# URL buffer
urls = deque()

# Stores images
prev_image = None
current_image = None

if platform.system() != 'Darwin':
    # Running on RasPI
    import board
    import neopixel

    # Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
    # NeoPixels must be connected to D10, D12, D18 or D21 to work.
    pixel_pin = board.D18

    # The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
    # For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
    ORDER = neopixel.GRB

    pixels = neopixel.NeoPixel(pixel_pin, NUM_PIXELS, brightness=1, auto_write=False,
                               pixel_order=ORDER)
else:
    # Running on local machine
    import fakeneopixel

    pixels = fakeneopixel.NeoPixel(num_pixels=NUM_PIXELS)

# Switch to the current dir
os.chdir(os.path.dirname(os.path.realpath(__file__)))


class XmasImage():
    def __init__(self, bytes, name):
        self.name = name
        img = Image.open(BytesIO(bytes))
        image = img.resize((NUM_PIXELS - BLACK_OFFSET, NUM_PIXELS - BLACK_OFFSET), resample=Image.BICUBIC)
        image = image.filter(ImageFilter.GaussianBlur(radius=BLUR_PIXELS))
        image = image.resize((NUM_PIXELS - BLACK_OFFSET, HEIGHT_TO_WIDTH * NUM_PIXELS),
                             resample=Image.BICUBIC)

        # Desaturate
        converter = ImageEnhance.Color(image)
        image = converter.enhance(COLOR_LEVEL)
        self.image = ImageOps.autocontrast(image, cutoff=0, ignore=None)

    def gamma(self, v, gamma=0.5):
        v = int((v / 255) ** (1 / gamma) * 255)
        return v

    def max_level(self, v):
        return int(v / 255 * MAX_LEVEL)

    def get_row(self, y):
        row = [(0, 0, 0)] * BLACK_OFFSET
        if y > self.image.size[1]:
            raise ("Requested row %d larger than image height %d" % (y, self.image.size[1]))
        else:

            for x in range(0, self.image.size[0]):
                pixel = [self.max_level(self.gamma(p, gamma=0.6)) for p in self.image.getpixel((x, y))]
                row.append(pixel)
            return row


def log(msg):
    print(msg)


def get_next_url():
    """
    If the url-buffer is empty, fetches a new set of URLs from instagram
    :return:
    """
    global urls, url_pointer

    if len(urls) < 2:
        done = False
        while not done:
            print("Fetching new URLs")
            r = requests.get(
                'http://instagram-images-silvan-privat.appuioapp.ch/fetch?url=https://www.instagram.com/explore/tags/christmas/')
            if r.status_code == 200:
                urls.extend(r.json())
                if len(urls) > 0:
                    print("%d urls collected" % len(urls))
                    done = True
                else:
                    print("Service provided 0 URLs")
            else:
                print("Connection error. Status %s" % r.status_code)
    else:
        print("Use existing URLs. %d left" % len(urls))
    return urls.popleft()


def get_next_image():
    """
    Checks that we have two images in our image buffer
    :return:
    """
    while (len(images) < 2):
        url = get_next_url()
        print("Fetching URL %s" % url)
        r = requests.get(url)
        if r.status_code == 200:
            images.append(XmasImage(r.content, url))
            print("%d bytes fetched" % len(r.content))

    return images.popleft()


def check_is_night_via_webservice():
    """
    Returns True if it's night.
    :return: boolean
    """
    r = requests.get('https://api.sunrise-sunset.org/json?lat=47.376888&lng=8.541694&formatted=0')
    if r.status_code == 200:
        response = r.json()
        sunrise = dateparser.parse(response['results']['sunrise']) + timedelta(minutes=30)
        sunset = dateparser.parse(response['results']['sunset']) - timedelta(minutes=30)
        its_night = datetime.now(pytz.utc) < sunrise or datetime.now(pytz.utc) > sunset
        log("It's night? %s " % ('yes' if its_night else 'no'))
        return its_night
    else:
        log("Unknown sunrise/sunset")
        return None


def prevent_darkness(tuple):
    """ Makes sure that the RGB values are never (0,0,0) to prevent too much contrast """
    return [1 if v == 0 else v for v in tuple]


def get_row_using_crossfade(y):
    """ Returns the current row considering crossfade effects.
    :param y: Current row number
    :return: all color values for one row
    """
    global current_image, prev_image

    row = current_image.get_row(y)
    # print("imag_index=%d, pos=%d" % (image_index, y), end="\r")
    if y >= OVERLAP_ROWS or prev_image is None:
        # no overlap
        pass
    else:
        # has overlap
        row = current_image.get_row(y)
        prev_row = prev_image.get_row(NUM_PIXELS * HEIGHT_TO_WIDTH - OVERLAP_ROWS + y)
        for x in range(0, NUM_PIXELS):
            new_color_tuple = [0, 0, 0]
            for channel in range(0, 3):
                new_color_tuple[channel] = int(
                    (1 - y / OVERLAP_ROWS) * prev_row[x][channel]) \
                                           + int((y / OVERLAP_ROWS) * row[x][channel])

                assert row[x][channel] >= 0 and row[x][channel] < 256
            row[x] = tuple(new_color_tuple)
    return row


def display_image():
    global prev_image, current_image

    # Start with a random image
    current_image_index = 0
    lights_on = True
    last_stats = None

    while True:
        # Getting a new image. Previous images is kept for crossfade effect
        prev_image = current_image
        current_image = get_next_image()

        # Turn the lights on?
        is_night = check_is_night_via_webservice()
        if is_night is not None:
            lights_on = is_night

        current_image_name = current_image.name

        if datetime.now().hour < 6:
            log("turn off between 0 AM and 6 AM")
            lights_on = False
            current_image_name = ''

        if last_stats is not None:
            with open('current_image_stats.json', 'w') as f:
                last_stats['image_name'] = current_image_name
                f.write(json.dumps(last_stats))

        log("Current image displayed %s" % current_image.name)
        last_stats = {
            'timestamp_start': time.time(),
            'timestamp_end': None,
        }
        for y in range(0, NUM_PIXELS * HEIGHT_TO_WIDTH - OVERLAP_ROWS):
            row = get_row_using_crossfade(y)
            for index, val in enumerate(row):
                if index < NUM_PIXELS:
                    if lights_on and index > BLACK_OFFSET:
                        pixels[index] = tuple(prevent_darkness(val))
                    else:
                        pixels[index] = (0, 0, 0)
            pixels.show()
            time.sleep(ANIMATION_DELAY)
        current_image_index = (current_image_index + 1) % len(images)
        last_stats['timestamp_end'] = time.time()


def test():
    log("Run test.")
    for x in range(0, NUM_PIXELS):
        pixels[x] = (0, 0, 0)

    for x in range(BLACK_OFFSET, NUM_PIXELS):
        i = x / 255 * pi * 5
        level = x / NUM_PIXELS * 255
        pixels[x] = (
            int((sin(i) + 1) / 2 * level), int((cos(i * 2) + 1) / 2 * level), int((sin(i * 3) + 1) / 2 * level))
        pixels.show()


# while True:
test()
check_is_night_via_webservice()
display_image()
