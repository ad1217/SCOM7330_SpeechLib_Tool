import sys

from audiolib import Header
from config import bin


def main():
    with open(sys.argv[1], 'rb') as f:
        data = f.read()

    header = Header.from_bytes(data)

    print(header)

    remaining = data[0x100:]
    while len(remaining) > 0:
        print(remaining[0])
        for record_class in bin.ConfigRecord.__subclasses__():
            if remaining[0] == record_class.record_type:
                orig = remaining
                record, remaining = record_class.from_bytes(remaining)
                print(record)
                print(orig[:len(record.to_bytes())])
                print(record.to_bytes())
                break


if __name__ == '__main__':
    main()
