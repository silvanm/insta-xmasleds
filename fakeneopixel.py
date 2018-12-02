""" Simulates the NeoPixel as image """

from PIL import Image

IMAGE_HEIGHT = 1000


class NeoPixel:
    def __init__(self, num_pixels=0):
        self.num_pixels = num_pixels
        self.image_index = 0
        self.reset()

    def init_buffer(self):
        self.buffer = [(0, 0, 0)] * self.num_pixels

    def __setitem__(self, key, value):
        assert isinstance(key, int)
        assert isinstance(value, tuple)
        assert len(value) == 3
        self.buffer[key] = value

    def show(self):
        for x in range(0, self.num_pixels):

            self.image.putpixel((x, self.y), self.buffer[x])

        self.y += 1
        if self.y >= IMAGE_HEIGHT:
            self.save("image_%d.jpg" % self.image_index)
            self.image_index += 1
            self.reset()

    def save(self, path):
        output = open(path, "w")
        self.image.save(output, quality=90)
        print("Saving to %s" % path)

    def reset(self):
        self.y = 0
        self.image = Image.new(mode='RGB', size=(self.num_pixels, IMAGE_HEIGHT))
        self.init_buffer()
