#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path

import scomspeech


def info(input_file: Path) -> None:
    with open(input_file, 'rb') as f:
        data = f.read()

    speechLib = scomspeech.SpeechLib.from_bytes(data)

    print(speechLib.header)
    print(speechLib.imageHeader)

    print("Audio Data:")
    for word_code, offset in speechLib.index.word_offsets.items():
        entry = speechLib.audioData.entries[word_code]
        stop = int.from_bytes(data[offset:offset + 3], "big")
        length = len(entry.data)
        print(f"  word code: {word_code:<5} "
              f"start: 0x{offset:<6X} "
              f"end: 0x{stop:<6X} "
              f"length: 0x{length:<6X} ({length} bytes)")


def extract_audio(input_file: Path, output_dir: Path) -> None:
    speechLib = scomspeech.SpeechLib.from_file(input_file)

    output_dir.mkdir(exist_ok=True)

    for word_code, entry in speechLib.audioData.entries.items():
        with open(output_dir / f"{word_code}.raw", 'wb') as f:
            f.write(entry.data)


def generate_CustomAudioLib(input_dir: Path, output_file: Path) -> None:
    speechLib = scomspeech.SpeechLib.from_directory(input_dir)

    with open(output_file, 'wb') as f:
        f.write(speechLib.to_bytes())


def main():
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
        extract_audio(args.input_file, args.output_dir)


if __name__ == '__main__':
    main()
