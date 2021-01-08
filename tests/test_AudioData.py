import unittest
from unittest import mock

from scomspeech import AudioData, AudioDataEntry, AudioLengthException


class TestAudioDataEntry(unittest.TestCase):
    def test_to_bytes(self) -> None:
        audio_data = AudioDataEntry(b'12345')
        audio_data_bytes = audio_data.to_bytes(0x1000)

        self.assertEqual(audio_data_bytes, b'\x00\x10\x0712345')

    def test_high_byte_inversion(self) -> None:
        # anything > 0x7f should have the lower 7 bits inverted
        audio_data = AudioDataEntry(b'\x80\x82\xff\x7fasdf')
        audio_data_bytes = audio_data.to_bytes(0x1000)

        self.assertEqual(audio_data_bytes[3:], b'\xff\xfd\x80\x7fasdf')

    def test_from_bytes(self) -> None:
        audio_data = AudioDataEntry.from_bytes(b'\xff\xff\x00\x00\x081234', 2)

        self.assertEqual(audio_data, AudioDataEntry(b'1234'))

    def test_from_bytes_out_of_bounds(self) -> None:
        with self.assertRaises(IndexError):
            AudioDataEntry.from_bytes(b'\x00\x10\x001234', 0)


class TestAudioData(unittest.TestCase):
    def test_to_bytes(self) -> None:
        # TODO: should this respect the offsets in the index, or just concat?
        audioData = AudioData({
            1: mock.Mock(**{'to_bytes.return_value': b'1234'}),
            2: mock.Mock(**{'to_bytes.return_value': b'5678'}),
        })

        index = mock.Mock(word_offsets={
            1: 0x100,
            2: 0x200,
        })

        self.assertEqual(audioData.to_bytes(index), b'12345678')

    def test_from_files(self) -> None:
        # TODO
        pass

    def test_check_audio_length_ok(self) -> None:
        audioData = AudioData({
            1: mock.Mock(data=b'\x00' * (5760000)),
        })

        audioData.check_audio_length()

    def test_check_audio_length_too_long(self) -> None:
        audioData = AudioData({
            1: mock.Mock(data=b'\x00' * (5760000 + 1)),
        })

        with self.assertRaises(AudioLengthException):
            audioData.check_audio_length()


if __name__ == '__main__':
    unittest.main()
