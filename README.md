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


## Disclaimer

I am not affiliated with S-COM in any way. I make no guarantees of the
correctness of the code. Don't break your stuff.
