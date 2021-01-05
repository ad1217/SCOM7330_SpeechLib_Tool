#!/usr/bin/env python3

import os
import sys
from datetime import datetime
from typing import BinaryIO, ByteString, Dict, Optional


def arbitrary_round(x: int, base: int) -> int:
    return base * round(x / base)


def invert_high_byte(byte: int) -> int:
    # I have no idea why their code does this
    if byte > 127:
        return byte ^ 127
    else:
        return byte


def pack_file(filename: str, output_file: BinaryIO) -> None:
    with open(filename, 'rb') as input_file:
        data = input_file.read()
    # calculate the position of the end of the file, including the
    # 3 bytes for this stop number.
    oSLStop = (output_file.tell() + len(data) + 2).to_bytes(3, 'big')
    encoded_file = oSLStop + bytes(invert_high_byte(byte) for byte in data)

    output_file.write(encoded_file)


def make_index(index_size: int, word_offsets: Dict[int, int]) -> ByteString:
    index = bytearray(b'\xff' * index_size)
    for word_code, offset in word_offsets.items():
        index[word_code * 4:word_code * 4 + 3] = offset.to_bytes(3, 'big')

    return index


def assign_pos(header: bytearray, pos: int, content: ByteString) -> None:
    header[pos:pos + len(content)] = content


def make_header(firstFree: int, timestamp: Optional[str] = None,
                version: str = "1.0.0", mode: int = 3) -> ByteString:
    if timestamp is None:
        now = datetime.now()
        timestamp = now.strftime("%m/%y/%d %H:%M")
    header = bytearray(b'\xff' * 0x100)
    assign_pos(header, 0, b"SCOM\x00")  # static string
    assign_pos(header, 5, b"SCOM Cust ALib")  # static string
    assign_pos(header, 16 + 5, b"1.0.0")   # version, static in source
    assign_pos(header, 2 * 16 + 1, timestamp.encode('ascii'))  # timestamp
    header[3*16 + 8] = 3  # 3 in normal mode, 2 in extended arguments mode
    # TODO: why is this -0x100? seems to be ignoring this header?
    assign_pos(header, 3*16 + 9, (firstFree - 0x100).to_bytes(3, "big"))
    # there were arguments to the original function, but the function
    # was passed literal zeros...
    assign_pos(header, 3*16 + 12, b'\x00\x00\x00\x00')

    # sanity check
    assert len(header) == 0x100

    return header


def make_imageHeader(index_size: int, max_word: int, firstFree: int) -> ByteString:
    header = bytearray(b'\xff' * 0x100)

    header[0:3] = [0, 2, 0]  # constants in source
    header[3] = index_size.to_bytes(3, "big")[1]
    header[4:6] = (max_word + 1).to_bytes(3, "big")[1:3]  # TODO: why is this +1?
    header[6:9] = firstFree.to_bytes(3, "big")

    # sanity check
    assert len(header) == 0x100

    return header


def generate_CustomAudioLib(input_dir: str, output_filename: str) -> None:
    with open(output_filename, 'wb') as f:
        word_files = sorted(os.listdir(input_dir))
        max_word = max(int(word_file.partition('.')[0]) for word_file in word_files)

        # each element in the index is 4 bytes (but only uses 3)
        # total size is rounded up to nearest 0x100
        index_size = arbitrary_round(max_word * 4, 0x100)
        print(f"Maximum word: {max_word} (0x{max_word:X}), index size: {index_size}, (0x{index_size:X})")

        f.seek(0x200 + index_size)
        word_offsets = {}
        for word_file in word_files:
            word_code = int(word_file.partition('.')[0])
            word_offsets[word_code] = f.tell()
            print(f"word code: {word_code} start: 0x{f.tell():06X}")
            pack_file(input_dir + '/' + word_file, f)

        firstFree = f.tell()
        f.seek(0)
        f.write(bytes(make_header(firstFree)))
        f.write(bytes(make_imageHeader(index_size, max_word, firstFree)))
        f.write(bytes(make_index(index_size, word_offsets)))


if __name__ == '__main__':
    input_dir = './CustomAudioFiles'
    output_file = 'CustomAudioLib.bin'

    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    generate_CustomAudioLib(input_dir, output_file)
