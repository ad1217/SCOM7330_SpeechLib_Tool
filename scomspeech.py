import logging

from datetime import datetime
from pathlib import Path
from typing import ByteString, Dict, Iterable, Optional, Tuple, TypedDict

TIMESTAMP_FORMAT = "%m/%d/%y %H:%M"
DATE_FORMAT = "%m/%d/%Y"

MAX_AUDIO_LENGTH = 12.0
AUDIO_SAMPLE_RATE = 8000  # 8kHz


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


def arbitrary_round(x: int, base: int) -> int:
    return base * round(x / base)


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


def assign_pos(header: bytearray, pos: int, content: ByteString) -> None:
    header[pos:pos + len(content)] = content


def make_header(firstFree: int, name: bytes = b"SCOM Cust ALib",
                timestamp: Optional[bytes] = None,
                version: str = "1.0.0", mode: int = 3) -> ByteString:
    if timestamp is None:
        now = datetime.now()
        timestamp = now.strftime(TIMESTAMP_FORMAT).encode('ascii')
    header = bytearray(b'\xff' * 0x100)
    assign_pos(header, 0x00, b"SCOM\x00")  # static string
    assign_pos(header, 0x05, name)
    assign_pos(header, 0x15, b"1.0.0")   # version, static in source
    assign_pos(header, 0x21, timestamp)  # timestamp
    header[0x38] = 3  # 3 in normal mode, 2 in extended arguments mode
    # TODO: why is this -0x100? seems to be ignoring this header?
    assign_pos(header, 0x39, (firstFree - 0x100).to_bytes(3, "big"))
    # there were arguments to the original function, but the function
    # was passed literal zeros...
    assign_pos(header, 0x3c, b'\x00\x00\x00\x00')

    # sanity check
    assert len(header) == 0x100

    return header


def parse_imageHeader(header: bytes) -> ImageHeader:
    return {
        "preamble": header[0:3],  # constants in source
        # only the middle byte is stored
        "index_size": header[3] << 8,
        # TODO: why is this +1?
        "max_word": int.from_bytes(header[4:6], "big"),
        "firstFree": int.from_bytes(header[6:9], "big"),
    }


def make_imageHeader(index_size: int, max_word: int, firstFree: int) -> ByteString:
    header = bytearray(b'\xff' * 0x100)

    header[0:3] = [0, 2, 0]  # constants in source
    header[3] = index_size.to_bytes(3, "big")[1]
    header[4:6] = (max_word + 1).to_bytes(3, "big")[1:3]  # TODO: why is this +1?
    header[6:9] = firstFree.to_bytes(3, "big")

    # sanity check
    assert len(header) == 0x100

    return header


def parse_index(index: bytes) -> Dict[int, int]:
    def get_address(index: bytes, word_code: int) -> int:
        return int.from_bytes(index[word_code * 4: word_code * 4 + 3], "big")

    return {word_code: address
            for word_code in range(0, len(index) // 4)
            if (address := get_address(index, word_code)) != 0xffffff}


def make_index(index_size: int, word_offsets: Dict[int, int]) -> ByteString:
    index = bytearray(b'\xff' * index_size)
    for word_code, offset in word_offsets.items():
        index[word_code * 4:word_code * 4 + 3] = offset.to_bytes(3, 'big')

    return index


def invert_high_byte(byte: int) -> int:
    # I have no idea why their code does this
    if byte > 127:
        return byte ^ 127
    else:
        return byte


def extract_audio_data(data: ByteString, offset: int) -> bytes:
    stop = int.from_bytes(data[offset:offset + 3], "big")

    return bytes(invert_high_byte(byte) for byte in data[offset + 3:stop + 1])


def pack_audio_data(data: ByteString, offset: int) -> ByteString:
    # calculate the position of the end of the file, including the
    # 3 bytes for this stop number.
    oSLStop = (offset + len(data) + 2).to_bytes(3, 'big')
    return oSLStop + bytes(invert_high_byte(byte) for byte in data)


def pack_word_files(word_files: Iterable[Path],
                    base_offset: int) -> Tuple[Dict[int, int], ByteString]:
    word_offsets = {}
    out_data = bytearray()

    for word_file in word_files:
        word_code = int(word_file.stem)
        offset = base_offset + len(out_data)
        word_offsets[word_code] = offset
        logging.info(f"word code: {word_code} start: 0x{offset:06X}")

        with open(word_file, 'rb') as input_file:
            data = input_file.read()
            out_data += pack_audio_data(data, offset)

    return word_offsets, out_data


def check_audio_length(data_length: int) -> None:
    """calculate minutes of audio and compare with max"""
    # TODO: this includes the file end pointers, which it probably shouldn't.
    audio_length = data_length / (AUDIO_SAMPLE_RATE * 60)
    if audio_length > MAX_AUDIO_LENGTH:
        raise Exception(
            f"You have {audio_length:.2f} minutes of custom audio "
            f"but the maximum is {MAX_AUDIO_LENGTH} minutes.\n"
            "Please remove or shorten some custom words")
