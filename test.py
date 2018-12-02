import unittest
from os import unlink

from fakeneopixel import NeoPixel
import filecmp


class TestFakeNeopixel(unittest.TestCase):

    def test_create_image(self):
        img = NeoPixel(num_pixels=100)
        for x in range(0, 100):
            img[x] = (x * 2, x * 2, x * 2)
            img.show()
        img.save('data/image.jpg')
        self.assertTrue(filecmp.cmp('data/image.jpg', 'data/expected.jpg'))

    def tearDown(self):
        unlink('data/image.jpg')

if __name__ == '__main__':
    unittest.main()
