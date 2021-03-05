#!/usr/bin/env python3

import sys

import construct as cs
import construct_typed as cst
from datetime import datetime

from .audiolib import Header
from .config import bin


def main():
    with open(sys.argv[1], 'rb') as f:
        data = f.read()

    header = Header.from_bytes(data)

    print(header)

    remaining = data[0x100:]
    parsers = bin.ConfigRecord.get_parsers()
    format = cs.GreedyRange(cs.Select(*parsers)) >> cs.HexDump(cs.GreedyBytes)

    test = format.parse(remaining)
    print(test[0])
    print('next leftover:', test[1][:10])


if __name__ == '__main__':
    main()
