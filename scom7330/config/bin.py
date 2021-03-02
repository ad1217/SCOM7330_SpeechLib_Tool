from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple


class ConfigRecord:
    record_type: int

    @staticmethod
    def _unpack_date(data: bytes) -> datetime:
        """Datetime is represented in packed bcd"""
        def bcd_to_int(bcd_num: int) -> int:
            return (bcd_num >> 4) * 10 + (bcd_num & 0xf)

        ints = [bcd_to_int(n) for n in reversed(data[0:7])]

        print(ints)

        # TODO: figure out what the middle byte (data[3]) is
        # might be day of week, with mon = 1 ?
        return datetime(year=2000 + ints[0], month=ints[1], day=ints[2],
                        hour=ints[4], minute=ints[5], second=ints[6])

    @staticmethod
    def _pack_date(date: datetime) -> bytes:
        def int_to_bcd(num: int) -> int:
            return ((num // 10) << 4) + (num % 10)

        return bytes([
            int_to_bcd(date.second),
            int_to_bcd(date.minute),
            int_to_bcd(date.hour),
            date.weekday() + 1,  # TODO: speculative
            int_to_bcd(date.day),
            int_to_bcd(date.month),
            int_to_bcd(date.year - 2000),
        ])

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple[ConfigRecord, bytes]:
        raise NotImplementedError

    def to_bytes(self) -> bytes:
        raise NotImplementedError


@dataclass
class Controller(ConfigRecord):
    record_type = 0
    element_size = 0x20
    num_elements = 1

    attributes: int
    signature: bytes
    structure_version: int
    controller_firmware_version: str
    configuration_version: int
    controller_cold_reset_datetime: datetime
    receivers: int
    transmitters: int
    password_digits: int
    macro_name_digits: int
    macro_attr_size: int
    num_config_records: int

    @property
    def controller_type(self):
        return f'7{self.receivers}{self.transmitters}0'

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple[Controller, bytes]:
        record_type = data[0]
        assert record_type == cls.record_type
        attributes = data[1]
        element_size = data[2]
        assert element_size == cls.element_size
        num_elements = data[3]
        assert num_elements == cls.num_elements

        record = cls(
            attributes=attributes,
            signature=data[4:8],
            structure_version=data[8],
            controller_firmware_version=f'{data[9]}.{data[0xa]}.{data[0xb]}',
            configuration_version=data[0xc],
            controller_cold_reset_datetime=cls._unpack_date(data[0xd:0x1e]),
            receivers=data[0x1e],
            transmitters=data[0x1f],
            password_digits=data[0x20],
            macro_name_digits=data[0x21],
            macro_attr_size=data[0x22],
            num_config_records=data[0x23],
        )

        return record, data[4 + element_size * num_elements:]

    def to_bytes(self) -> bytes:
        return bytes([
            self.record_type,
            self.attributes,
            self.element_size,
            self.num_elements,
            *self.signature,
            self.structure_version,
            *[int(b) for b in self.controller_firmware_version[::2]],
            self.configuration_version,
            *self._pack_date(self.controller_cold_reset_datetime).ljust(17, b'\xff'),
            self.receivers,
            self.transmitters,
            self.password_digits,
            self.macro_name_digits,
            self.macro_attr_size,
            self.num_config_records,
        ])


@dataclass
class ID(ConfigRecord):
    record_type = 1
    element_size = 0x36
    num_elements = 1

    attributes: int
    controller_model_number: str
    controller_serial_number: str
    controller_manufacture_datetime: datetime
    controller_format_datetime: datetime
    original_customer_name: str

    @staticmethod
    def _parse_null_str(data: bytes) -> str:
        return data.partition(b'\x00')[0].decode('ascii')

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple[ID, bytes]:
        record_type = data[0]
        assert record_type == cls.record_type
        attributes = data[1]
        element_size = data[2]
        assert element_size == cls.element_size
        num_elements = data[3]
        assert num_elements == cls.num_elements

        print(data[4:4 + element_size])

        record = cls(
            attributes,
            controller_model_number=cls._parse_null_str(data[0x4:0xc]),
            controller_serial_number=cls._parse_null_str(data[0xc:0x22]),
            controller_manufacture_datetime=cls._unpack_date(data[0x14:0x1b]),
            controller_format_datetime=cls._unpack_date(data[0x1b:0x22]),
            original_customer_name=cls._parse_null_str(data[0x22:0x3a]),
        )

        return record, data[4 + element_size:]

    def to_bytes(self) -> bytes:
        return bytes([
            self.record_type,
            self.attributes,
            self.element_size,
            self.num_elements,
            *self.controller_model_number.encode('ascii').ljust(8, b'\x00'),
            *self.controller_serial_number.encode('ascii').ljust(8, b'\x00'),
            *self._pack_date(self.controller_manufacture_datetime),
            *self._pack_date(self.controller_format_datetime),
            *self.original_customer_name.encode('ascii').ljust(24, b'\x00'),
        ])


class Status(ConfigRecord):
    record_type = 2


class FWVer(ConfigRecord):
    record_type = 3


class Serial(ConfigRecord):
    record_type = 4


@dataclass
class Name(ConfigRecord):
    record_type = 5
    element_size = 17
    num_elements = 1

    attributes: int
    controller_name: str

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple[Name, bytes]:
        record_type = data[0]
        assert record_type == cls.record_type
        attributes = data[1]
        element_size = data[2]
        assert element_size == cls.element_size
        num_elements = data[3]
        assert num_elements == cls.num_elements

        name = data[4:4 + element_size].strip(b'\x00').decode('ascii')

        record = cls(attributes, name)

        return record, data[4 + element_size * num_elements:]

    def to_bytes(self) -> bytes:
        return bytes([
            self.record_type,
            self.attributes,
            self.element_size,
            self.num_elements,
            *self.controller_name.encode('ascii').ljust(self.element_size, b'\x00')
        ])


@dataclass
class Passwords(ConfigRecord):
    record_type = 6
    element_size = 1

    attributes: int

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple[Passwords, bytes]:
        record_type = data[0]
        assert record_type == cls.record_type
        attributes = data[1]
        element_size = data[2]
        num_elements = data[3]

        return cls(attributes), data[4 + element_size * num_elements:]


class SoftwareSwitch(ConfigRecord):
    record_type = 7


class EventTrigMacro(ConfigRecord):
    record_type = 8


class SchedulerSetpoint(ConfigRecord):
    record_type = 9


class Macros(ConfigRecord):
    record_type = 10


class Timers10(ConfigRecord):
    record_type = 0xb
#     element_size =

#     attributes: int
#     num_misc: int
#     num_port: int

#     @classmethod
#     def from_bytes(cls, data: bytes) -> Tuple[Timers10, bytes]:
#          record_type = data[0]
#          assert record_type == cls.record_type
#          attributes = data[1]
#          element_size = data[2]
#          num_misc = data[3]
#          num_port = data[4]


class Timers100(ConfigRecord):
    record_type = 0xc


class Timers1000(ConfigRecord):
    record_type = 0xd


class Counters(ConfigRecord):
    record_type = 0xe
    # element_size =

    # attributes: int
    # num_misc: int
    # num_port: int

    # @classmethod
    # def from_bytes(cls, data: bytes) -> Tuple[Counters, bytes]:
    #      record_type = data[0]
    #      assert record_type == cls.record_type
    #      attributes = data[1]
    #      element_size = data[2]
    #      num_misc = data[3]
    #      num_port = data[4]



class Messages(ConfigRecord):
    record_type = 0xf


class PathMode(ConfigRecord):
    record_type = 0x10


class PathPriority(ConfigRecord):
    record_type = 0x11


class CTCSSEncoders(ConfigRecord):
    record_type = 0x12


class IDTail(ConfigRecord):
    record_type = 0x13


class MessageHandlers(ConfigRecord):
    record_type = 0x14


class DTMFDecoders(ConfigRecord):
    record_type = 0x15


@dataclass
class CPWAccessTable(ConfigRecord):
    record_type = 0x16
    element_size = 1

    attributes: int
    elements: list[bool]

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple[CPWAccessTable, bytes]:
        record_type = data[0]
        assert record_type == cls.record_type
        attributes = data[1]
        element_size = data[2]
        assert element_size == cls.element_size
        num_elements = data[3]

        elements = [bool(el) for el in data[4:4 + num_elements]]
        return cls(attributes, elements), data[4 + num_elements:]

    def to_bytes(self) -> bytes:
        return bytes([self.record_type, self.attributes,
                      self.element_size, len(self.elements), *self.elements])

    # def to_commands(self) -> list[SCOMCommand]:
    #     for root_number, element in enumerate(elements):
    #         if element[root_number]:
    #             yield AssignControlOperatorPrivilegeLevel(root_number, True)


class UserTimers(ConfigRecord):
    record_type = 0x17


class CmdRespRouting(ConfigRecord):
    record_type = 0x18


class ToneGenerators(ConfigRecord):
    record_type = 0x19


class LongNames(ConfigRecord):
    record_type = 0x1a
