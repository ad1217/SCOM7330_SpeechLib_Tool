#!/usr/bin/env python3

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, TypedDict

from scom_speechlib_tool import invert_high_byte, DATE_FORMAT, TIMESTAMP_FORMAT


class Header(TypedDict):
    preamble: bytes
    name: bytes
    version: bytes
    timestamp: datetime
    mode: int
    firstFree: int
    zeros: bytes


class ImageHeader(TypedDict):
    preamble: bytes
    index_size: int
    max_word: int
    firstFree: int


def parse_header(header: bytes) -> Header:
    timestamp_raw = header[0x21:].partition(b"\xff")[0].decode('ascii')
    try:
        timestamp = datetime.strptime(timestamp_raw, TIMESTAMP_FORMAT)
    except ValueError:
        timestamp = datetime.strptime(timestamp_raw, DATE_FORMAT)

    return {
        "preamble": header[0x00:0x05],  # constant
        "name": header[0x05:].partition(b"\xff")[0],
        "version": header[0x15:].partition(b"\xff")[0],
        "timestamp": timestamp,
        "mode": header[0x38],
        "firstFree": int.from_bytes(header[0x39:0x39 + 3], "big"),
        # these were literal 0s in the source...
        "zeros": header[0x3c:0x3c + 4],
    }


def parse_imageHeader(header: bytes) -> ImageHeader:
    return {
        "preamble": header[0:3],  # constants in source
        # only the middle byte is stored
        "index_size": header[3] << 8,
        # TODO: why is this +1?
        "max_word": int.from_bytes(header[4:6], "big"),
        "firstFree": int.from_bytes(header[6:9], "big"),
    }


def parse_index(index: bytes) -> Dict[int, int]:
    def get_address(index: bytes, word_code: int) -> int:
        return int.from_bytes(index[word_code * 4: word_code * 4 + 3], "big")

    return {word_code: address
            for word_code in range(0, len(index) // 4)
            if (address := get_address(index, word_code)) != 0xffffff}


def extract_audio_file(data, offset) -> bytes:
    stop = int.from_bytes(data[offset:offset + 3], "big")

    return bytes(invert_high_byte(byte) for byte in data[offset + 3:stop + 1])


def parse_CustomAudioLib(input_filepath: Path, output_dir: Path) -> None:
    with open(input_filepath, 'rb') as f:
        data = f.read()

    orig_header = data[0:0x100]
    header = parse_header(orig_header)
    print("Header:", header)

    orig_imageHeader = data[0x100:0x200]
    imageHeader = parse_imageHeader(orig_imageHeader)
    print("Image Header:", imageHeader)

    orig_index = data[0x200:0x200 + imageHeader["index_size"]]
    index = parse_index(orig_index)
    print("Word codes:", list(index.keys()))

    for word_code, offset in index.items():
        with open(output_dir / f"{word_code}.raw", 'wb') as f:
            f.write(extract_audio_file(data, offset))


if __name__ == '__main__':
    input_file = Path('CustomAudioLib.bin')
    output_dir = Path('CustomAudioFiles')

    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    if not output_dir.exists():
        output_dir.mkdir()

    parse_CustomAudioLib(input_file, output_dir)
