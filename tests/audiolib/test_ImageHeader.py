import unittest

from scom7330.audiolib import ImageHeader

class TestImageHeader(unittest.TestCase):
    def test_to_bytes(self) -> None:
        imageHeader = ImageHeader(0x1000, 1024, 0x1234)

        imageHeader_bytes = imageHeader.to_bytes()
        self.assertEqual(len(imageHeader_bytes), 0x100)
        self.assertEqual(
            imageHeader_bytes,
            b'\x00\x02\x00\x10\x04\x01\x00\x124'.ljust(0x100, b'\xff'))

    def test_from_bytes(self) -> None:
        pass
        imageHeader = ImageHeader.from_bytes(
            b'\x00\x02\x00\x10\x04\x01\x00\x124'.ljust(0x100, b'\xff'))

        self.assertEqual(imageHeader, ImageHeader(0x1000, 1024, 0x1234))


if __name__ == '__main__':
    unittest.main()
