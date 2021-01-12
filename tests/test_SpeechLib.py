import json
import unittest
from hashlib import md5
from pathlib import Path

from scomspeech import Header, ImageHeader, Index, SpeechLib


class TestSpeechLib(unittest.TestCase):
    def test_from_bytes(self) -> None:
        # TODO
        pass

    def test_from_file(self) -> None:
        # TODO
        pass

    def test_from_directory(self) -> None:
        # TODO
        pass


class TestSpeechLib_Read_SpLibEng(unittest.TestCase):
    source_file = Path('./tests/data/SpLibEng_1.3.bin')
    source_url = "http://www.scomcontrollers.com/downloads/SpLibEng_1.3.bin"
    source_hash = '4e2d170c5b6fb7ab7be9565ac594ecf2'

    speechLib: SpeechLib

    @classmethod
    def setUpClass(cls) -> None:
        if not cls.source_file.is_file():
            raise unittest.SkipTest(
                f"Missing {cls.source_file} from {cls.source_url}")

        with open(cls.source_file, 'rb') as f:
            data = f.read()

        if md5(data).hexdigest() != cls.source_hash:
            raise unittest.SkipTest(
                f"{cls.source_file} has wrong hash, "
                f"please re-download from {cls.source_url}")

        cls.speechLib = SpeechLib.from_bytes(data)

    def test_headers(self) -> None:
        self.assertEqual(self.speechLib.header,
                         Header(firstFree=7741549,
                                name=b'SCOM Sp Lib Eng',
                                version=b'1.3.0',
                                timestamp_raw=b'2/17/2017',
                                mode=2))

        self.assertEqual(self.speechLib.imageHeader,
                         ImageHeader(index_size=0x1A00,
                                     max_word=1630,
                                     firstFree=7741549))

    def test_index(self) -> None:
        with open(self.source_file.with_suffix('.offsets.json')) as f:
            expected_offsets = {int(k): v for k, v in json.load(f).items()}

        self.assertEqual(self.speechLib.index, Index(0x1A00, expected_offsets))

    def test_contents(self) -> None:
        with open(self.source_file.with_suffix('.md5sums.json')) as f:
            expected_sums = {int(k): v for k, v in json.load(f).items()}

        sums = {word_code: md5(entry.data).hexdigest()
                for word_code, entry in self.speechLib.audioData.entries.items()}

        self.assertEqual(sums, expected_sums)


class TestSpeechLib_Read_DemoAudioLib(unittest.TestCase):
    source_file = Path('./tests/data/DemoAudioLib.bin')
    source_url = "http://www.scomcontrollers.com/downloads/7330_V1.8b_191125.zip"
    source_hash = '3828b3ddc9c6b5e9ca1df0d7638d4074'

    speechLib: SpeechLib

    @classmethod
    def setUpClass(cls) -> None:
        if not cls.source_file.is_file():
            raise unittest.SkipTest(
                f"Missing {cls.source_file} from {cls.source_url}")

        with open(cls.source_file, 'rb') as f:
            data = f.read()

        if md5(data).hexdigest() != cls.source_hash:
            raise unittest.SkipTest(
                f"{cls.source_file} has wrong hash, "
                f"please re-download from {cls.source_url}")

        cls.speechLib = SpeechLib.from_bytes(data)

    def test_headers(self) -> None:
        self.assertEqual(self.speechLib.header,
                         Header(firstFree=1104265,
                                timestamp_raw=b'09/09/09 12:00'))

        self.assertEqual(self.speechLib.imageHeader,
                         ImageHeader(index_size=0x3F00,
                                     max_word=4002,
                                     firstFree=1104265))

    def test_index(self) -> None:
        expected_offsets = {
            4000: 16640,
            4001: 1056259,
            4002: 1080262
        }

        self.assertEqual(self.speechLib.index, Index(0x3F00, expected_offsets))

    def test_contents(self) -> None:
        expected_sums = {
            4000: '9a6ec0e8b543e922cdff09e1ccffe927',
            4001: '8f3d3cb828ce507cf38968835382ffb4',
            4002: 'bb62511d46ffcf6d0e4d6a1e0798a928'
        }

        sums = {word_code: md5(entry.data).hexdigest()
                for word_code, entry in self.speechLib.audioData.entries.items()}

        self.assertEqual(sums, expected_sums)


if __name__ == '__main__':
    unittest.main()
