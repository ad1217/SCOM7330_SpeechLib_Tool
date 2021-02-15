from enum import Enum, EnumMeta
from collections.abc import Iterable
from typing import cast, TypeVar, Type

from pyparsing import Char, Or, ParserElement, Word, nums, ParseResults

DTMF_CHARS = nums + 'ABCD'

# Basic token types

BOOLEAN = Char('01')


class NumWord(Word):
    def __init__(self, exact: int = 0, **kwargs):
        super().__init__(nums, exact=exact, **kwargs)


def Integer(max_value: int, max_chars: int = 0, exact_chars: int = 0) -> ParserElement:
    return Word(nums, max=max_chars, exact=exact_chars) \
        .addParseAction(lambda toks: int(toks[0])) \
        .addCondition(lambda toks: toks[0] <= max_value)


UINT16 = Integer(max_chars=5, max_value=65535)


def EnumKey(enum: EnumMeta) -> ParserElement:
    return Or([str(t.name) for t in cast(Iterable[Enum], enum)]) \
        .addParseAction(lambda x: enum[x])


def EnumValue(enum: EnumMeta, zfill: int = 0) -> ParserElement:
    return Or([str(t.value).zfill(zfill) for t in cast(Iterable[Enum], enum)]) \
        .addParseAction(lambda x: enum(int(x[0])))


DTMFP = TypeVar('DTMFP', bound='DTMFParsable')


class DTMFParsable:
    parser: ParserElement

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def from_dtmf(cls: Type[DTMFP], tokens: ParseResults) -> DTMFP:
        print(cls.__name__)
        return cls(**tokens[0].asDict())

    def to_dtmf(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_parser(cls):
        return cls.parser.copy() \
                         .setParseAction(cls.from_dtmf) \
                         .setName(cls.__name__)
