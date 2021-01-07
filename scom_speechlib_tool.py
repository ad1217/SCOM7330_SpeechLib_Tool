#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path

import scomspeech


def info(input_file: Path) -> None:
    with open(input_file, 'rb') as f:
        data = f.read()

    orig_header = data[0:0x100]
    header = scomspeech.Header.from_bytes(orig_header)
    print(header)

    orig_imageHeader = data[0x100:0x200]
    imageHeader = scomspeech.ImageHeader.from_bytes(orig_imageHeader)
    print(imageHeader)

    orig_index = data[0x200:0x200 + imageHeader.index_size]
    index = scomspeech.Index.from_bytes(orig_index)

    print("Index:")
    for word_code, offset in index.word_offsets.items():
        stop = int.from_bytes(data[offset:offset + 3], "big")
        length = stop - offset - 3
        print(f"  word code: {word_code:<5} "
              f"start: 0x{offset:<6X} "
              f"end: 0x{stop:<6X} "
              f"length: 0x{length:<6X} ({length} bytes)")


def parse_CustomAudioLib(input_file: Path, output_dir: Path) -> None:
    with open(input_file, 'rb') as f:
        data = f.read()

    orig_imageHeader = data[0x100:0x200]
    imageHeader = scomspeech.ImageHeader.from_bytes(orig_imageHeader)

    orig_index = data[0x200:0x200 + imageHeader.index_size]
    index = scomspeech.Index.from_bytes(orig_index)

    for word_code, offset in index.word_offsets.items():
        with open(output_dir / f"{word_code}.raw", 'wb') as f:
            f.write(scomspeech.AudioDataEntry.from_audio_data(data, offset).data)


def generate_CustomAudioLib(input_dir: Path, output_file: Path) -> None:
    word_files = sorted(
        f for f in input_dir.iterdir()
        if f.stem.isdigit() and f.suffix == '.raw'
        and int(f.stem) >= 3000 and int(f.stem) < 5000)

    word_data = scomspeech.AudioData.from_files(word_files)
    word_data.check_audio_length()

    index = scomspeech.Index.from_AudioData(word_data)
    word_data_bytes = word_data.to_bytes(index)

    firstFree = 0x200 + index.index_size + len(word_data_bytes)

    with open(output_file, 'wb') as f:
        f.write(scomspeech.Header(firstFree).to_bytes())
        f.write(scomspeech.ImageHeader(index.index_size, index.max_word, firstFree).to_bytes())
        f.write(index.to_bytes())
        f.write(word_data_bytes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-l", "--log", dest="logLevel",
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default="WARNING",
                        help="Set the logging level")

    subparsers = parser.add_subparsers(title="Subcommands",
                                       dest='subcommand',
                                       description='Use -h on a subcommand for more info',
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

    parser_info = subparsers.add_parser(
        'info',
        help="Print some information about the contents of a speech lib",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_info.add_argument('input_file',
                                type=Path,
                                nargs='?',
                                default='CustomAudioLib.bin',
                                help="The input audio library file")

    args = parser.parse_args()

    logging.basicConfig(
        format="{levelname}: {message}",
        style='{',
        level=logging.getLevelName(args.logLevel))

    if args.subcommand == 'create':
        generate_CustomAudioLib(args.input_dir, args.output_file)
    elif args.subcommand == 'info':
        info(args.input_file)
    elif args.subcommand == 'extract':
        parse_CustomAudioLib(args.input_file, args.output_dir)
