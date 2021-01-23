from datetime import datetime
import unittest
from unittest import mock

from scomspeech import Header


class TestHeaderTimestamp(unittest.TestCase):
    def test_timestamp_both(self) -> None:
        with self.assertRaises(ValueError):
            Header(0, timestamp=datetime(2020, 1, 1), timestamp_raw=b'')

    def test_timestamp_bytes_date(self) -> None:
        header = Header(0, timestamp_raw=b'04/05/2020')
        self.assertEqual(header.timestamp, datetime(2020, 4, 5))

    def test_timestamp_bytes_datetime(self) -> None:
        header = Header(0, timestamp_raw=b'06/07/20 13:42')
        self.assertEqual(header.timestamp, datetime(2020, 6, 7, 13, 42))

    def test_timestamp_datetime(self) -> None:
        header = Header(0, timestamp=datetime(2020, 1, 2, 3, 45))
        self.assertEqual(header.timestamp_raw, b'01/02/20 03:45')

    def test_timestamp_None(self) -> None:
        expected_now = datetime(2020, 6, 7, 8, 32)
        with mock.patch('scomspeech.scomspeech.datetime') as mock_datetime:
            mock_datetime.now.return_value = expected_now

            header = Header(0)
            self.assertEqual(header.timestamp, expected_now)
            self.assertEqual(header.timestamp_raw, b'06/07/20 08:32')


class TestHeader(unittest.TestCase):
    def test_to_bytes(self) -> None:
        header = Header(0x1234, timestamp_raw=b'asdf')

        header_bytes = header.to_bytes()
        self.assertEqual(len(header_bytes), 0x100)
        self.assertEqual(
            header_bytes,
            b'SCOM\x00SCOM Cust ALib\xff\xff1.0.0\xff\xff\xff\xff\xff\xff\xffasdf\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x03\x00\x114\x00\x00\x00\x00'.ljust(0x100, b'\xff'))

    def test_from_bytes(self) -> None:
        header = Header.from_bytes(b'SCOM\x00SCOM Cust ALib\xff\xff1.0.0\xff\xff\xff\xff\xff\xff\xffasdf\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x03\x00\x114\x00\x00\x00\x00'.ljust(0x100, b'\xff'))

        self.assertEqual(header, Header(0x1234, timestamp_raw=b'asdf'))


if __name__ == '__main__':
    unittest.main()
