from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ByteString, Dict, Iterable, Optional


@dataclass
class Header:
    TIMESTAMP_FORMAT = "%m/%d/%y %H:%M"
    DATE_FORMAT = "%m/%d/%Y"

    firstFree: int
    preamble: bytes = b'SCOM\x00'  # static string
    name: bytes = b"SCOM Cust ALib"
    version: bytes = b"1.0.0"  # static in source
    timestamp: Optional[datetime] = None
    timestamp_raw: Optional[bytes] = None
    mode: int = 3  # 3 in normal mode, 2 in extended arguments mode
    # there were two arguments to the original function, but the
    # function was passed literal zeros...
    zeros: bytes = b'\x00\x00\x00\x00'

    def __post_init__(self) -> None:
        if self.timestamp is not None and self.timestamp_raw is not None:
            raise ValueError("Can't set both timestamp and timestamp_raw")

        elif self.timestamp_raw is not None:
            # inconsistent format in source vs example files
            try:
                self.timestamp = datetime.strptime(
                    self.timestamp_raw.decode('ascii'), self.TIMESTAMP_FORMAT)
            except ValueError:
                try:
                    self.timestamp = datetime.strptime(
                        self.timestamp_raw.decode('ascii'), self.DATE_FORMAT)
                except ValueError:
                    logging.debug(
                        f"Failed to parse timestamp bytes, ignoring: {self.timestamp_raw!s}")

        else:
            if self.timestamp is None:
                self.timestamp = datetime.now()
            self.timestamp_raw = self.timestamp.strftime(self.TIMESTAMP_FORMAT).encode('ascii')

    @classmethod
    def from_bytes(cls, header: bytes) -> Header:
        return cls(
            preamble=header[0x00:0x05],
            name=header[0x05:].partition(b"\xff")[0],
            version=header[0x15:].partition(b"\xff")[0],
            timestamp_raw=header[0x21:].partition(b"\xff")[0],
            mode=header[0x38],
            firstFree=int.from_bytes(header[0x39:0x39 + 3], "big"),
            # these were literal 0s in the source...
            zeros=header[0x3c:0x3c + 4],
        )

    def _assign_pos(self, header: bytearray, pos: int, content: ByteString) -> None:
        header[pos:pos + len(content)] = content

    def to_bytes(self) -> bytes:
        # __post_init__ should guarentee that this will always have a value
        assert self.timestamp_raw is not None

        header = bytearray(b'\xff' * 0x100)
        self._assign_pos(header, 0x00, self.preamble)
        self._assign_pos(header, 0x05, self.name)
        self._assign_pos(header, 0x15, self.version)
        self._assign_pos(header, 0x21, self.timestamp_raw)
        header[0x38] = self.mode
        # TODO: why is this -0x100? seems to be ignoring this header?
        self._assign_pos(header, 0x39, (self.firstFree - 0x100).to_bytes(3, "big"))
        self._assign_pos(header, 0x3c, self.zeros)

        # sanity check
        assert len(header) == 0x100

        return bytes(header)

    def __str__(self) -> str:
        return "\n".join([
            "Header:",
            f"  preamble: {self.preamble!s}",
            f"  name: {self.name!s}",
            f"  version: {self.version!s}",
            f"  timestamp: {self.timestamp!s}",
            f"  mode: {self.mode}",
            f"  firstFree: 0x{self.firstFree:X}",
            f"  zeros: {self.zeros!s}"
        ])


@dataclass
class ImageHeader:
    index_size: int
    max_word: int
    firstFree: int
    preamble: bytes = b'\x00\x02\x00'   # constants in source

    @classmethod
    def from_bytes(cls, header: bytes) -> ImageHeader:
        return cls(
            preamble=header[0:3],
            # only the middle byte is stored
            index_size=header[3] << 8,
            max_word=int.from_bytes(header[4:6], "big"),
            firstFree=int.from_bytes(header[6:9], "big"),
        )

    def to_bytes(self) -> bytes:
        header = bytearray(b'\xff' * 0x100)

        header[0:3] = [0, 2, 0]  # constants in source
        header[3] = self.index_size.to_bytes(3, "big")[1]
        header[4:6] = (self.max_word + 1).to_bytes(3, "big")[1:3]  # TODO: why is this +1?
        header[6:9] = self.firstFree.to_bytes(3, "big")

        # sanity check
        assert len(header) == 0x100

        return bytes(header)

    def __str__(self) -> str:
        return "\n".join([
            "Image Header:",
            f"  preamble: {self.preamble!s}",
            f"  index_size: 0x{self.index_size:X} ({self.index_size//4} words)",
            f"  max_word: {self.max_word}",
            f"  firstFree: 0x{self.firstFree:X} ({self.firstFree} bytes)",
        ])


@dataclass
class Index:
    index_size: int
    word_offsets: Dict[int, int]
    max_word: int = field(init=False)

    def __post_init__(self) -> None:
        self.max_word = max(self.word_offsets.keys())

        logging.info(f"Maximum word: {self.max_word} (0x{self.max_word:X}), "
                     f"Index Size: {self.index_size}, (0x{self.index_size:X})")

    @staticmethod
    def arbitrary_round(x: int, base: int) -> int:
        return base * round(x / base)

    # TODO: not sure I like the coupling here, but couldn't think of a
    # cleaner way to do this
    @classmethod
    def from_AudioData(cls, audioData: AudioData, base_offset: int = 0x200) -> Index:
        # each element in the index is 4 bytes (but only uses 3)
        # total size is rounded up to nearest 0x100
        max_word = max(audioData.entries.keys())
        index_size = cls.arbitrary_round(max_word * 4, 0x100)

        word_offsets = {}
        offset = base_offset + index_size

        for word_code, entry in audioData.entries.items():
            word_offsets[word_code] = offset
            logging.info(f"word code: {word_code} start: 0x{offset:06X}")
            offset += len(entry.data) + 3

        return cls(index_size, word_offsets)

    @classmethod
    def from_bytes(cls, index: bytes) -> Index:
        def get_address(index: bytes, word_code: int) -> int:
            return int.from_bytes(index[word_code * 4: word_code * 4 + 3], "big")

        word_codes = {word_code: address
                      for word_code in range(0, len(index) // 4)
                      if (address := get_address(index, word_code)) != 0xffffff}

        return cls(len(index), word_codes)

    def to_bytes(self) -> bytes:
        index = bytearray(b'\xff' * self.index_size)
        for word_code, offset in self.word_offsets.items():
            index[word_code * 4:word_code * 4 + 3] = offset.to_bytes(3, 'big')

        return bytes(index)


@dataclass
class AudioDataEntry:
    data: bytes

    @staticmethod
    def _invert_high_byte(byte: int) -> int:
        # I have no idea why their code does this
        if byte > 127:
            return byte ^ 127
        else:
            return byte

    @classmethod
    def from_audio_data(cls, audio_data: ByteString, offset: int) -> AudioDataEntry:
        stop = int.from_bytes(audio_data[offset:offset + 3], "big")

        return cls(bytes(cls._invert_high_byte(byte)
                         for byte in audio_data[offset + 3:stop + 1]))

    def to_audio_data(self, offset: int) -> bytes:
        # calculate the position of the end of the file, including the
        # 3 bytes for the stop number.
        stop = (offset + len(self.data) + 2)

        inverted_bytes = bytes(self._invert_high_byte(byte) for byte in self.data)
        return stop.to_bytes(3, 'big') + inverted_bytes


@dataclass
class AudioData:
    MAX_AUDIO_LENGTH = 12.0
    AUDIO_SAMPLE_RATE = 8000  # 8kHz

    entries: Dict[int, AudioDataEntry]

    @classmethod
    def from_files(cls, word_files: Iterable[Path]) -> AudioData:
        entries = {}

        for word_file in word_files:
            word_code = int(word_file.stem)
            with open(word_file, 'rb') as input_file:
                entries[word_code] = AudioDataEntry(input_file.read())

        return cls(entries)

    def to_bytes(self, index: Index, base_offset: int = 0x200) -> bytes:
        out_data = bytes()
        for word_code, offset in index.word_offsets.items():
            out_data += self.entries[word_code].to_audio_data(offset)

        return out_data

    def check_audio_length(self) -> None:
        """Calculate minutes of audio and compare with max"""
        data_length = sum(len(entry.data) for entry in self.entries.values())
        audio_length = data_length / (self.AUDIO_SAMPLE_RATE * 60)
        if audio_length > self.MAX_AUDIO_LENGTH:
            raise Exception(
                f"You have {audio_length:.2f} minutes of custom audio "
                f"but the maximum is {self.MAX_AUDIO_LENGTH} minutes.\n"
                "Please remove or shorten some custom words")
