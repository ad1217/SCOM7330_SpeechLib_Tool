# SCOM 7330 Custom Speech Library Tool

This is a tool to generate Custom Audio Libraries
(`CustomAudioLib.bin`) for the SCOM 7330 repeater, reverse engineered
from the provided `BuildSpeechLib.exe`.

## `CustomAudioLib.bin` Format

The `CustomAudioLib.bin` file is composed of 4 sections:

- header (`0x100` bytes)
- image header (`0x100` bytes)
- word index (variable length, rounded up to the nearest `0x100`)
- data (variable length)

The header and image header contain metadata and the word index is a
lookup table into the data. Unused space is filled with `0xff` instead
of `0x00`, for unclear reasons.

<!-- (TODO: finish description) -->


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
