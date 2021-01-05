# SCOM 7330 Speech Library Tool

This is a tool to manipulate Audio Libraries (such as
`CustomAudioLib.bin`) for the SCOM 7330 repeater, reverse engineered
from the provided `BuildSpeechLib.exe`.

The official tool, as well as default audio libraries, manuals,
firmware, etc. can be found at
http://www.scomcontrollers.com/7330firmware .

## Speech Library Format

The speech library file is composed of 4 sections:

- [Header](#header) (`0x100` bytes)
- [Image Header](#image-header) (`0x100` bytes)
- [Word Index](#word-index) (variable length, rounded up to the nearest `0x100`)
- [Word Data](#word-data) (variable length)

The header and image header contain metadata and the word index is a
lookup table into the data. Unused space is filled with `0xff` instead
of `0x00`, for unclear reasons.

In the following sections, byte ranges are presented as
`inclusive:exclusive`, like in Python. For example, `0x00:0x05`
includes the bytes `0x00`, `0x01`, `0x02`, `0x03`, and `0x04`. All
addresses in tables are relative to the start of the section, unless
stated otherwise.

### Header

- Address: `0x00`
- Length: `0x100`

| Byte  | 0x00:0x05  | 0x05:0x15 | 0x15:0x21 | 0x21:0x38 | 0x38 | 0x39:0x3c | 0x3c:0x3d | 0x3d:0x100 |
|:------|:-----------|:----------|:----------|:----------|:-----|:----------|:----------|:-----------|
| Value | `SCOM\x00` | name      | version   | timestamp | mode | firstFree | zeros     | (empty)    |

- `name`, `version`, and `timestamp` are just ASCII strings, and have
  no apparent function beyond display.
- `mode` is 3 in `BuildSpeechLib.exe`'s normal mode, 2 in the extended
  arguments form. I am not sure what this means, exactly.
- `firstFree` is the size of the file minus `0x100`, presumably to
  account for this header's size. Unclear what this is used for, as it
  also occurs (with the `0x100` included) in the [Image Header](#image-header)
- `zeros` is two two-byte arguments to the function in
  `BuildSpeechLib.exe` which were passed in as literal zeros. Unclear
  function.

### Image Header

- Address: `0x100`
- Length: `0x100`

| Byte  | 0x00:0x03      | 0x03           | 0x04:0x06    | 0x06:0x09 | 0x09:0x100 |
|:------|:---------------|:---------------|:-------------|:----------|:-----------|
| Value | `\x00\x02\x00` | index_size_mid | max_word + 1 | firstFree | (empty)    |

- I'm not sure what the purpose of the constant in `0x00:0x03` is
- `index_size_mid` is the middle byte of the [Word Index](#word-index)
  size. Since that size is rounded to `0x100`, this is just the index
  size shifted down 1 byte.
- `max_word + 1` is the highest word file contained, plus one.
  Not really sure why it's plus one.
- `firstFree` is the length of the file.
  Seems to be redundant with the value in the [Header](#header).

### Word Index

- Address: `0x200`
- Length: 4 times the maximum word code, rounded up to the nearest `0x100`

| Byte  | (word code * 4):(word code * 4) + 3 |
|:------|:------------------------------------|
| Value | word data address                   |

This section is a lookup table mapping the word code to the address of
the entry in the [Word Data](#word-data) section, relative to the file
start. All un-used entries are blank (`0xff`). Each entry is 4 bytes
long, but the address is stored just in the first 3 bytes (with the
last one being `0xff`.

### Word Data

- Address: `0x200` plus the the length of the [Word Index](#word-index),
  as stored in the [Image Header](#image-header).
- Length: 3 times the number of files, plus the length of each file

For each entry:
| Byte  | 0x00:0x03                | 0x03:end of file |
|:------|:-------------------------|:-----------------|
| Value | end of file data address | file data        |

- `end of file data address` is the address of the end of the audio file data.
- `file data` is the contents of a raw file (as per
  [Audio Files](#audio-files)), but with every byte greater than 127 xor'ed
  with 127 for some unclear reason.


## Audio Files

The input/output audio files are in the format specified in the SCOM manual:

- 8000 Hertz sampling rate
- Single channel (mono) audio
- μ-law encoding
- Raw headerless file

You can convert wav files (for example) to this format with `sox`:

```sh
sox --type wav <input file>.wav --type ul --rate 8k <output file>.raw
```

or from this format to wav:

```sh
sox --type ul --rate 8k --channels 1 <input file>.raw --type wav <output file>.wav
```


## Disclaimer

I am not affiliated with S-COM in any way. I make no guarantees of the
correctness of the code. Don't break your stuff.
