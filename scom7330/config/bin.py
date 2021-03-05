from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

import construct as cs
import construct_typed as cst
from construct_typed import TStructField as SF


# TODO: ideally this would be derived from the controller record,
#       but I don't want to do that quite yet
PORT_NUM = 3
MACRO_LENGTH = 4  # 4 DTMF characters, typically 2 bytes


class BCDByte(cs.Adapter):
    def _decode(self, obj: int, context: cs.Context, path: cs.PathType) -> int:
        return (obj >> 4) * 10 + (obj & 0xf)

    def _encode(self, obj: int, context: cs.Context, path: cs.PathType) -> int:
        return ((obj // 10) << 4) + (obj % 10)


class HexString(cs.Adapter):
    def _decode(self, obj: bytes, context: cs.Context, path: cs.PathType) -> str:
        return obj.hex()

    def _encode(self, obj: str, context: cs.Context, path: cs.PathType) -> bytes:
        return bytes.fromhex(obj)


class BCDDatetimeAdapter(cs.Adapter):
    def _decode(self, obj: list[int], context: cs.Context, path: cs.PathType) -> datetime:
        # TODO: figure out what the middle (obj[3]) byte is
        # might be day of week, with mon = 1 ?
        return datetime(year=2000 + obj[6], month=obj[5], day=obj[4],
                        hour=obj[2], minute=obj[1], second=obj[0])

    def _encode(self, obj: datetime, context: cs.Context, path: cs.PathType) -> list[int]:
        return [
            obj.second,
            obj.minute,
            obj.hour,
            obj.weekday() + 1,  # TODO: speculative
            obj.day,
            obj.month,
            obj.year - 2000,
        ]


class FileVersionAdapter(cs.Adapter):
    def _decode(self, obj: list[int], context: cs.Context, path: cs.PathType) -> str:
        if obj[0] == 0x7f:
            return 'no file'
        elif obj[0] == 0xff:
            return "version not set"
        else:
            return '.'.join(str(n) for n in obj)

    def _encode(self, obj: str, context: cs.Context, path: cs.PathType) -> list[int]:
        if obj == 'no file':
            return [0x7f, 0xff, 0xff]
        elif obj == "version not set":
            return [0x7f, 0xff, 0xff]
        else:
            return [int(x) for x in obj.split('.')]


BCDDatetime = BCDDatetimeAdapter(BCDByte(cs.Byte)[7])
FileVersion = FileVersionAdapter(cs.Byte[3])


class ConfigRecord:
    records: list[cst.TContainerBase] = []

    @classmethod
    def register(cls, record):
        cls.records.append(record)
        return record

    @classmethod
    def get_parsers(cls):
        return [cst.TStruct(c) for c in cls.records]


@ConfigRecord.register
@dataclass
class Controller(cst.TContainerBase):
    record_type: int = SF(cs.Const(0, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x20, cs.Byte))
    num_elements: int = SF(cs.Const(1, cs.Byte))

    signature: bytes = SF(cs.Bytes(4))
    structure_version: int = SF(cs.Byte)
    controller_firmware_version: str = SF(FileVersion)
    configuration_version: int = SF(cs.Byte)
    controller_cold_reset_datetime: datetime = SF(cs.Padded(17, BCDDatetime, b'\xff'))
    receivers: int = SF(cs.Byte)
    transmitters: int = SF(cs.Byte)
    password_digits: int = SF(cs.Byte)
    macro_name_digits: int = SF(cs.Byte)
    macro_attr_size: int = SF(cs.Byte)
    num_config_records: int = SF(cs.Byte)

    @property
    def controller_type(self):
        return f'7{self.receivers}{self.transmitters}0'


@ConfigRecord.register
@dataclass
class ID(cst.TContainerBase):
    record_type: int = SF(cs.Const(1, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x36, cs.Byte))
    num_elements: int = SF(cs.Const(1, cs.Byte))

    controller_model_number: str = SF(cs.PaddedString(8, 'ascii'))
    controller_serial_number: str = SF(cs.PaddedString(8, 'ascii'))
    controller_manufacture_datetime: datetime = SF(BCDDatetime)
    controller_format_datetime: datetime = SF(BCDDatetime)
    original_customer_name: str = SF(cs.PaddedString(24, 'ascii'))


@ConfigRecord.register
@dataclass
class Status(cst.TContainerBase):
    record_type: int = SF(cs.Const(2, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x5, cs.Byte))
    num_elements: int = SF(cs.Const(1, cs.Byte))

    # 0 = "Out/Active-Low"
    # 1 = "In/Active-High"
    cor: list[bool] = SF(cs.BitsSwapped(cs.Bitwise(cs.Padded(8, cs.Flag[PORT_NUM]))))
    ctcss: list[bool] = SF(cs.BitsSwapped(cs.Bitwise(cs.Padded(8, cs.Flag[PORT_NUM]))))
    ptt: list[bool] = SF(cs.BitsSwapped(cs.Bitwise(cs.Padded(8, cs.Flag[PORT_NUM]))))

    # 0 = "Out"
    # 1 = "In" (probably)
    aux: list[bool] = SF(cs.BitsSwapped(cs.Bitwise(cs.Padded(8, cs.Flag[5]))))

    unknown: int = SF(cs.Byte) # TODO


@ConfigRecord.register
@dataclass
class FWVer(cst.TContainerBase):
    record_type: int = SF(cs.Const(3, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x30, cs.Byte))
    num_elements: int = SF(cs.Const(1, cs.Byte))

    BootROM: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    SBOOT: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    Diagnostics: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    # TODO: figure out a better way of handling this?
    unknown: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    SCOM_A: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    SCOM_B: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    Configuration_A: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    Configuration_B: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    Configuration_C: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    Configuration_D: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    Custom_Audio_Library: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))
    Speech_Library: bytes = SF(cs.Padded(4, FileVersion, b'\xff'))


@ConfigRecord.register
@dataclass
class Serial(cst.TContainerBase):
    record_type: int = SF(cs.Const(4, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x10, cs.Byte))
    num_elements: int = SF(cs.Const(1, cs.Byte))

    serial_signature: bytes = SF(HexString(cs.Bytes(2)))
    console_baud_rate: int = SF(cs.Byte)  # TODO: make into an enum
    unknown1: int = SF(cs.Byte)  # TODO
    aux_baud_rate: int = SF(cs.Byte)  # TODO: make into an enum
    unknown2: bytes = SF(cs.Bytes(2))  # TODO
    second_is_console: bool = SF(cs.Flag)  # determines which port is console vs aux
    unknown3: bytes = SF(cs.Bytes(8))  # TODO

    # speeds = ["57600", "38400", "19200", " 9600", " 4800", " 2400", " 1200",]
    # "Console,   %s, 8 data bits, no parity, no flow control, no modem control\n"
    # "Auxiliary, %s, 8 data bits, no parity, no flow control, no modem control\n"


@ConfigRecord.register
@dataclass
class Name(cst.TContainerBase):
    record_type: int = SF(cs.Const(5, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x11, cs.Byte))
    num_elements: int = SF(cs.Const(1, cs.Byte))

    controller_name: str = SF(cs.PaddedString(cs.this.element_size, 'ascii'))


@ConfigRecord.register
@dataclass
class Passwords(cst.TContainerBase):
    record_type: int = SF(cs.Const(6, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(3, cs.Byte))
    num_elements: int = SF(cs.Const(3, cs.Byte))

    # TODO: These are probably more dynamic in size...
    MPW: bytes = SF(cs.Hex(cs.Bytes(3)))  # TODO: trim trailing 0xFF, convert to string
    CPW: bytes = SF(cs.Hex(cs.Bytes(3)))  # TODO: trim trailing 0xFF, convert to string
    RBPW: bytes = SF(cs.Hex(cs.Bytes(3)))  # TODO: trim trailing 0xFF, convert to string


@ConfigRecord.register
@dataclass
class SoftwareSwitch(cst.TContainerBase):
    record_type: int = SF(cs.Const(7, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x32, cs.Byte))
    num_elements: int = SF(cs.Const(1, cs.Byte))

    # TODO: filter to printable/setable, map to names
    switches: list[bool] = SF(cs.BitsSwapped(cs.Bitwise(cs.Flag[400])))


@ConfigRecord.register
@dataclass
class EventTrigMacro(cst.TContainerBase):
    @dataclass
    class ETM(cst.TContainerBase):
        num: int = SF(cs.Byte)
        macro: str = SF(HexString(cs.Bytes(MACRO_LENGTH // 2)))

    record_type: int = SF(cs.Const(8, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(2, cs.Byte))
    num_misc: int = SF(cs.Const(100, cs.Byte))
    num_port: int = SF(cs.Const(100, cs.Byte))

    # TODO: map to names
    misc: list[ETM] = SF(cs.NullTerminated(cs.GreedyRange(cst.TStruct(ETM)), term=b'\xff'))
    port: list[list[ETM]] = SF(cs.NullTerminated(cs.GreedyRange(cst.TStruct(ETM)), term=b'\xff')[PORT_NUM])


@ConfigRecord.register
@dataclass
class SchedulerSetpoint(cst.TContainerBase):
    @dataclass
    class Setpoint(cst.TContainerBase):
        number: int = SF(cs.NoneOf(cs.Byte, b'\xff'))
        macro: bytes = SF(HexString(cs.Bytes(MACRO_LENGTH // 2)))
        unknown: int = SF(cs.Byte)  # TODO: seems to always be e0?
        # Note that this cannot be a datetime, since "99" means "every"
        month: bytes = SF(BCDByte(cs.Byte))
        day: bytes = SF(BCDByte(cs.Byte))
        hour: bytes = SF(BCDByte(cs.Byte))
        minute: bytes = SF(BCDByte(cs.Byte))
        flags: int = SF(cs.Byte)

    record_type: int = SF(cs.Const(9, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(8, cs.Byte))
    num_elements: int = SF(cs.Byte)

    # TODO: the reporter somehow derives if the scheduler is enabled

    setpoints: list[Setpoint] = SF(cs.FocusedSeq(
        "setpoint",
        "setpoint"/cs.GreedyRange(cst.TStruct(Setpoint)),
        cs.Const(0xff, cs.Byte)))


@ConfigRecord.register
@dataclass
class Macros(cst.TContainerBase):
    @dataclass
    class Macro(cst.TContainerBase):
        location: int = SF(cs.Int16ub)
        name: str = SF(cs.NullTerminated(HexString(cs.Bytes(MACRO_LENGTH // 2)), term=b'\xff'))
        # TODO: 0xe0 is *
        commands: list[bytes] = SF(cs.NullTerminated(
            cs.GreedyRange(cs.Prefixed(cs.Byte, HexString(cs.GreedyBytes), includelength=True)),
            term=b'\xff'))

    record_type: int = SF(cs.Const(0xa, cs.Byte))
    attributes: int = SF(cs.Byte)
    # TODO: this seems like it might be the max length of a macro?
    element_size: int = SF(cs.Byte)
    # max number of macros, hardcoded in the reporter
    num_elements: int = SF(cs.Const(0x154, cs.Int16ub))

    macros: list[Macro] = SF(cs.NullTerminated(cs.GreedyRange(cst.TStruct(Macro)), term=b'\xff\xff'))


@ConfigRecord.register
@dataclass
class Timers10(cst.TContainerBase):
    record_type: int = SF(cs.Const(0xb, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    # TODO: real values are multiplied by 10
    misc: list[int] = SF(cs.Int16ub[cs.this.num_misc])
    port: list[list[int]] = SF(cs.Int16ub[cs.this.num_port][PORT_NUM])


@ConfigRecord.register
@dataclass
class Timers100(cst.TContainerBase):
    record_type: int = SF(cs.Const(0xc, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    # TODO: real values are multiplied by 100
    misc: list[int] = SF(cs.Int16ub[cs.this.num_misc])
    port: list[list[int]] = SF(cs.Int16ub[cs.this.num_port][PORT_NUM])


@ConfigRecord.register
@dataclass
class Timers1000(cst.TContainerBase):
    record_type: int = SF(cs.Const(0xd, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    # TODO: real values are multiplied by 1000
    misc: list[int] = SF(cs.Int16ub[cs.this.num_misc])
    port: list[list[int]] = SF(cs.Int16ub[cs.this.num_port][PORT_NUM])


@ConfigRecord.register
@dataclass
class Counters(cst.TContainerBase):
    record_type: int = SF(cs.Const(0xe, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    misc: list[int] = SF(cs.Int16ub[cs.this.num_misc])
    port: list[list[int]] = SF(cs.Int16ub[cs.this.num_port][PORT_NUM])


@ConfigRecord.register
@dataclass
class Messages(cst.TContainerBase):
    @dataclass
    class Message(cst.TContainerBase):
        num: int = SF(cs.NoneOf(cs.Byte, b'\xff'))
        message: int = SF(HexString(cs.NullTerminated(cs.GreedyBytes, term=b'\xff')))

    record_type: int = SF(cs.Const(0xf, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(0x33, cs.Byte))
    num_misc: int = SF(cs.Const(25, cs.Byte))
    num_port: int = SF(cs.Const(14, cs.Byte))

    misc: list[Message] = SF(cs.FocusedSeq(
        "msg",
        "msg"/cs.GreedyRange(cst.TStruct(Message)),
        cs.Const(0xff, cs.Byte)))
    port: list[Message] = SF(cs.FocusedSeq(
        "msg",
        "msg"/cs.GreedyRange(cst.TStruct(Message)),
        cs.Const(0xff, cs.Byte))[PORT_NUM])


@ConfigRecord.register
@dataclass
class PathMode(cst.TContainerBase):
    @dataclass
    class PortPathMode(cst.TContainerBase):
        # TODO: probably shouldn't be nested like this
        class Mode(cst.EnumBase):
            No_Access = 0
            Carrier_Only = 1
            CTCSS_Only = 2
            Carrier_AND_CTCSS = 3
            Carrier_OR_CTCSS = 4
            Anti_CTCSS = 5
            Always_ON = 6
            Not_defined = 7

        # TODO: this depends on PORT_NUM being 3, should probably be more dynamic
        RXn_DTMF: int = SF(cst.TEnum(cs.Byte, Mode))
        RX1_TXn: int = SF(cst.TEnum(cs.Byte, Mode))
        RX2_TXn: int = SF(cst.TEnum(cs.Byte, Mode))
        RX3_TXn: int = SF(cst.TEnum(cs.Byte, Mode))

    record_type: int = SF(cs.Const(0x10, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(1, cs.Byte))
    num_misc: int = SF(cs.Const(0, cs.Byte))
    num_port: int = SF(cs.Const(4, cs.Byte))

    port: list[PortPathMode] = SF(cst.TStruct(PortPathMode)[PORT_NUM])


@ConfigRecord.register
@dataclass
class PathPriority(cst.TContainerBase):
    @dataclass
    class PortPathPriority(cst.TContainerBase):
        # TODO: ignore 0 bytes
        # TODO: ignore values outside of max number of ports
        priority: list[int] = SF(cs.Byte[cs.this._.element_size // 2])
        mixed: list[int] = SF(cs.Byte[cs.this._.element_size // 2])

    record_type: int = SF(cs.Const(0x11, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    port: list[PortPathPriority] = SF(cst.TStruct(PortPathPriority)[PORT_NUM])


@ConfigRecord.register
@dataclass
class CTCSSEncoders(cst.TContainerBase):
    @dataclass
    class PortCTCSSEncoder(cst.TContainerBase):
        tone_number: int = SF(cs.Byte)
        mode: int = SF(cs.Byte)  # TODO: make enum
        reverse_burst: int = SF(cs.Byte)  # TODO: maybe make enum

    record_type: int = SF(cs.Const(0x12, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    port: list[bytes] = SF(cst.TStruct(PortCTCSSEncoder)[PORT_NUM])


@ConfigRecord.register
@dataclass
class IDTail(cst.TContainerBase):
    @dataclass
    class PortIDTail(cst.TContainerBase):
        # TODO: 0xFFFF should be "None", 0xE should become '*', trailing 0xF stripped
        initial_ID_tail: int = SF(HexString(cs.Bytes(2)))
        normal_ID_tail: int = SF(HexString(cs.Bytes(2)))

    record_type: int = SF(cs.Const(0x13, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    port: list[bytes] = SF(cst.TStruct(PortIDTail)[PORT_NUM])


@ConfigRecord.register
@dataclass
class MessageHandlers(cst.TContainerBase):
    record_type: int = SF(cs.Const(0x14, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    # TODO: there's a lot of prettying up to do here...
    misc: bytes = SF(cs.Bytes(cs.this.num_misc))
    port: bytes = SF(cs.Bytes(cs.this.num_port)[PORT_NUM])


@ConfigRecord.register
@dataclass
class DTMFDecoders(cst.TContainerBase):
    record_type: int = SF(cs.Const(0x15, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Byte)

    # DTMF Commands Execute on Digit Count
    port: int = SF(cs.Byte[PORT_NUM])


@ConfigRecord.register
@dataclass
class CPWAccessTable(cst.TContainerBase):
    record_type: int = SF(cs.Const(0x16, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(1, cs.Byte))
    num_elements: int = SF(cs.Byte)

    # TODO: false is "Enabled", may want to invert
    # TODO: associate with names
    root_numbers: list[bool] = SF(cs.Flag[cs.this.num_elements])


@ConfigRecord.register
@dataclass
class UserTimers(cst.TContainerBase):
    class Resolution(cst.EnumBase):
        # TODO: better names
        _100ms = 0
        _10ms = 1
        _1s = 2
        _10s = 3

    record_type: int = SF(cs.Const(0x17, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(7, cs.Byte))
    num_elements: int = SF(cs.Byte)

    enable: list[bool] = SF(cs.Flag[cs.this.num_elements])
    timer_value: list[int] = SF(cs.Int16ub[cs.this.num_elements])
    # TODO: 0xff0000 is none, unclear what a set macro should be
    timeout_macro: list[str] = SF(HexString(cs.Bytes(3))[cs.this.num_elements])
    resolution: list[int] = SF(cst.TEnum(cs.Byte, Resolution)[cs.this.num_elements])


@ConfigRecord.register
@dataclass
class CmdRespRouting(cst.TContainerBase):
    record_type: int = SF(cs.Const(0x18, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Byte)
    num_elements: int = SF(cs.Byte)

    # TODO: what even is this?
    stuff: list[bytes] = SF(cs.Bytes(cs.this.element_size)[cs.this.num_elements])


@ConfigRecord.register
@dataclass
class ToneGenerators(cst.TContainerBase):
    @dataclass
    class PortToneGenerator(cst.TContainerBase):
        class Mode(cst.EnumBase):
            off = 0
            continuous = 1
            tone_on_when_ptt_keyed = 2
            tone_on_when_ptt_not_keyed = 3

        # TODO: 0 = "Message Handler", else "Tone Generator"
        owner: bool = SF(cs.Flag)
        mode: Mode = SF(cst.TEnum(cs.Byte, Mode))
        # TODO: convert to dB? (looks like just divide by 2?)
        message_level: int = SF(cs.Byte)
        # TODO: displayed as 4 digits, 2 digits per nibble
        # TODO: also maps to Hz, using (first_nibble * 5 + second_nibble + 0x104)
        tone_code: list[int] = SF(cs.Bitwise(cs.Nibble[2]))
        unknown: bytes = SF(cs.Bytes(3))

    record_type: int = SF(cs.Const(0x19, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(7, cs.Byte))
    num_misc: int = SF(cs.Const(0, cs.Byte))
    num_port: int = SF(cs.Const(1, cs.Byte))

    # TODO
    port: list[bytes] = SF(cst.TStruct(PortToneGenerator)[PORT_NUM])


@ConfigRecord.register
@dataclass
class LongNames(cst.TContainerBase):
    @dataclass
    class LongName(cst.TContainerBase):
        enable: bool = SF(cs.Flag)
        # TODO: convert to list of enabled ports, maybe an IntFlag
        ports: list[bool] = SF(cs.ByteSwapped(cs.Flag[7]))
        # TODO: starting with FF is "not set"
        macro: str = SF(cs.Bytewise(cs.Padded(4, HexString(cs.Bytes(MACRO_LENGTH // 2)), b'\xff')))
        name: str = SF(cs.Bytewise(cs.Padded(4, cs.NullTerminated(HexString(cs.GreedyBytes), term=b'\xff', require=False), b'\xff')))

    record_type: int = SF(cs.Const(0x1a, cs.Byte))
    attributes: int = SF(cs.Byte)
    element_size: int = SF(cs.Const(9, cs.Byte))
    num_misc: int = SF(cs.Byte)
    num_port: int = SF(cs.Const(0, cs.Byte))

    names: list[bytes] = SF(cst.TBitStruct(LongName)[cs.this.num_misc])

