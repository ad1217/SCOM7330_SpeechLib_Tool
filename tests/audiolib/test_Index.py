import unittest
from unittest import mock

from scom7330.audiolib import Index


class TestIndex(unittest.TestCase):
    def test_to_bytes(self) -> None:
        word_offsets = {
            1: 0x1234,
            2: 0x4567,
        }
        index = Index(0x100, word_offsets)

        index_bytes = index.to_bytes()
        self.assertEqual(len(index_bytes), 0x100)
        self.assertEqual(
            index_bytes,
            b'\xff\xff\xff\xff\x00\x124\xff\x00Eg'.ljust(0x100, b'\xff'))

    def test_from_bytes(self) -> None:
        index = Index.from_bytes(
            b'\xff\xff\xff\xff\x00\x124\xff\x00Eg'.ljust(0x100, b'\xff'))

        expected_word_offsets = {
            1: 0x1234,
            2: 0x4567,
        }

        self.assertEqual(index, Index(0x100, expected_word_offsets))

    def test_from_audioData(self) -> None:
        audioData = mock.Mock(entries={
            1: mock.Mock(data=b'\xff' * 0x1234),
            2: mock.Mock(data=b'\xff' * 0x4567),
        })
        index = Index.from_AudioData(audioData)

        self.assertEqual(index, Index(0x100, {1: 0x300, 2: 0x1537}))
        self.assertEqual(index.max_word, 2)


if __name__ == '__main__':
    unittest.main()
