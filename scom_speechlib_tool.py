#!/usr/bin/env python3

import argparse
from pathlib import Path

import scomspeech


def parse_CustomAudioLib(input_file: Path, output_dir: Path) -> None:
    with open(input_file, 'rb') as f:
        data = f.read()

    orig_header = data[0:0x100]
    header = scomspeech.parse_header(orig_header)
    print("Header:", header)

    orig_imageHeader = data[0x100:0x200]
    imageHeader = scomspeech.parse_imageHeader(orig_imageHeader)
    print("Image Header:", imageHeader)

    orig_index = data[0x200:0x200 + imageHeader["index_size"]]
    index = scomspeech.parse_index(orig_index)
    print("Word codes:", list(index.keys()))

    for word_code, offset in index.items():
        with open(output_dir / f"{word_code}.raw", 'wb') as f:
            f.write(scomspeech.extract_audio_data(data, offset))


def generate_CustomAudioLib(input_dir: Path, output_file: Path) -> None:
    word_files = sorted(
        f for f in input_dir.iterdir()
        if f.stem.isdigit() and f.suffix == '.raw'
        and int(f.stem) >= 3000 and int(f.stem) < 5000)
    max_word = max(int(word_file.stem) for word_file in word_files)

    # each element in the index is 4 bytes (but only uses 3)
    # total size is rounded up to nearest 0x100
    index_size = scomspeech.arbitrary_round(max_word * 4, 0x100)
    print(f"Maximum word: {max_word} (0x{max_word:X}), "
          f"Index Size: {index_size}, (0x{index_size:X})")

    word_offsets, word_data = scomspeech.pack_word_files(word_files, 0x200 + index_size)

    firstFree = 0x200 + index_size + len(word_data)

    scomspeech.check_audio_length((firstFree - (0x200 + index_size)))

    with open(output_file, 'wb') as f:
        f.write(bytes(scomspeech.make_header(firstFree)))
        f.write(bytes(scomspeech.make_imageHeader(index_size, max_word, firstFree)))
        f.write(bytes(scomspeech.make_index(index_size, word_offsets)))
        f.write(bytes(word_data))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(title="Subcommands",
                                       dest='subcommand',
                                       required=True)

    parser_create = subparsers.add_parser(
        'create',
        help="Pack audio into a audio library",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_create.add_argument('input_dir',
                               type=Path,
                               nargs='?',
                               default='CustomAudioFiles',
                               help="A directory with raw audio files to pack")
    parser_create.add_argument('output_file',
                               type=Path,
                               nargs='?',
                               default='CustomAudioLib.bin',
                               help="The output audio library file")

    parser_extract = subparsers.add_parser(
        'extract',
        help="Extract audio data from a speech lib",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_extract.add_argument('input_file',
                                type=Path,
                                nargs='?',
                                default='CustomAudioLib.bin',
                                help="The input audio library file")
    parser_extract.add_argument('output_dir',
                                type=Path,
                                nargs='?',
                                default='CustomAudioFiles',
                                help="A directory to which raw audio files will be written")

    args = parser.parse_args()

    if args.subcommand == 'create':
        generate_CustomAudioLib(args.input_dir, args.output_file)

    elif args.subcommand == 'extract':
        parse_CustomAudioLib(args.input_file, args.output_dir)
