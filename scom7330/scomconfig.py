from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Optional, Union

from pyparsing import (Char, Combine, Forward, Group, Or, Suppress, Word, nums,
                       restOfLine, ungroup)

from .dtmfparsing import (BOOLEAN, DTMF_CHARS, UINT16, DTMFParsable, EnumValue,
                          Integer, NumWord)
from .tables import MessageType, ValueType

PASSWD = Or([Word(DTMF_CHARS, exact=2), Word(DTMF_CHARS, exact=4), Word(DTMF_CHARS, exact=6)])
ROOT_NUMBER = NumWord(2)  # TODO: filter to root numbers in use?
MACRO_NAME = Word(nums + 'ABCD', max=4).setName('Short Macro Name')
FULL_MACRO_NAME = Word(nums + 'ABCD', exact=4).setName('Macro Name')
COUNTER_NUMBER = Suppress('0') + Char('0123')('port') + NumWord(2)('counter')
USER_TIMER = Integer(19, exact_chars=2)

MESSAGE_TYPE = EnumValue(MessageType)
VALUE_TYPE = EnumValue(ValueType)

# TODO: better message matching
MESSAGE = Group(NumWord()[...]).setName("Message")


COMMAND = Forward()


class SCOMCommand(DTMFParsable):
    root: str

    def apply(self, config: ConfigAcc) -> str:
        raise NotImplementedError()


@dataclass
class PasswordAndCommand(DTMFParsable):
    parser = Group(PASSWD('password') + COMMAND('command'))

    password: str
    command: SCOMCommand

    def to_dtmf(self):
        return f'{self.password} {self.command.to_dtmf()}'


PASSWD_AND_COMMAND = PasswordAndCommand.get_parser()
CMD_OR_MACRO = ungroup(PASSWD_AND_COMMAND ^ MACRO_NAME('macro'))


@dataclass
class ConfigAcc:
    macros: dict[str, list[Union[SCOMCommand, str]]] = field(default_factory=dict)
    switches: dict[str, bool] = field(default_factory=dict)


@dataclass
class ControlCTCSSEncoder(SCOMCommand):
    root = '02'
    parser = Group(Suppress(root) +
                   Char('123')('transmitter') +
                   Char('012345')('mode') +
                   Char('012')('reverse_burst'))

    transmitter: str
    mode: str
    reverse_burst: str

    def to_dtmf(self):
        return f'{self.root} {self.transmitter} {self.mode} {self.reverse_burst}'


@dataclass
class SelectCTCSSEncoderFrequency(SCOMCommand):
    root = '03'
    parser = Group(Suppress(root) +
                   Char('123')('transmitter') +
                   Integer(64, max_chars=2)('tone_number'))

    transmitter: str
    tone_number: int

    def to_dtmf(self):
        return f'{self.root} {self.transmitter} {self.tone_number}'


@dataclass
class SelectFrequencyofCW(SCOMCommand):
    root = '06'
    parser = Group(Suppress(root) +
                   Char('0123')('transmitter') + Suppress('0') +
                   NumWord(4)('tone_code'))

    transmitter: str
    tone_code: str

    def to_dtmf(self):
        return f'{self.root} {self.transmitter}0 {self.tone_code}'


@dataclass
class SelectFrequencyofSingleToneBeep(SCOMCommand):
    root = '06'
    parser = Group(Suppress(root) +
                   Suppress('0') + Char('123456')('beep') +
                   NumWord(4)('tone_code'))

    transmitter: str
    tone_code: str

    def to_dtmf(self):
        return f'{self.root} {self.transmitter}0 {self.tone_code}'


@dataclass
class SelectDefaultToneAndGapDurations(SCOMCommand):
    # TODO: limit duration names
    # TODO: some durations are only 01-99, while others are 00-99
    root = '08'
    parser = Group(Suppress(root) + NumWord(2)('duration_name') + NumWord(2)('duration'))

    duration_name: str
    duration: str

    def to_dtmf(self):
        return f'{self.root} {self.duration_name} {self.duration}'


@dataclass
class SetTimerValue(SCOMCommand):
    # TODO: some timers have more limitations on time values
    root = '09'
    parser = Group(Suppress(root) +
                   Char('012')('resolution') +
                   Char('0123')('port') +
                   NumWord(2)('timer') +
                   UINT16('time_value'))

    resolution: str
    port: str
    timer: str
    time_value: int

    def to_dtmf(self):
        return f'{self.root} {self.resolution}{self.port}{self.timer} {self.time_value}'


@dataclass
class SetDefaultMessageLevel(SCOMCommand):
    root = '10'
    parser = Group(Suppress(root) + Suppress('0') +
                   Char('123')('transmitter') +
                   Suppress('0') +
                   MESSAGE_TYPE('message_type') +
                   Integer(exact_chars=2, max_value=98)('level'))

    transmitter: str
    message_type: MessageType
    level: int

    def to_dtmf(self):
        return f'{self.root} 0{self.transmitter}0{self.message_type.value} {self.level:02}'


@dataclass
class SelectCWSpeed(SCOMCommand):
    root = '12'
    parser = Group(Suppress(root) +
                   Char('123')('transmitter') + Suppress('0') +
                   NumWord(1)('speed'))

    transmitter: str
    speed: str

    def to_dtmf(self):
        return f'{self.root} {self.transmitter} {self.speed}'


@dataclass
class CopyMessage(SCOMCommand):
    root = '13'
    parser = Group(Suppress(root) +
                   NumWord(4)('source_message_number') +
                   NumWord(4)('dest_message_number'))

    source_message_number: str
    dest_message_number: str

    def to_dtmf(self):
        return f'{self.root} {self.source_message_number} {self.dest_message_number}'


@dataclass
class SendMessage(SCOMCommand):
    root = '15'
    parser = Group(Suppress(root) + MESSAGE('message'))

    message: str

    def to_dtmf(self):
        return f'{self.root} {" ".join(self.message)}'


@dataclass
class StopSpeechInProgress(SCOMCommand):
    root = '16'
    parser = Group(Suppress(root) + Char('123')('ports*')[0,3])

    ports: Iterable[str]

    def to_dtmf(self):
        return f'{self.root} {" ".join(self.ports)}'


@dataclass
class CreateNewMacro(SCOMCommand):
    root = '20'
    parser = Group(Suppress(root) + FULL_MACRO_NAME('macro_name') + CMD_OR_MACRO('command'))

    macro_name: str
    command: Union[PasswordAndCommand, str]

    def to_dtmf(self):
        if type(self.command) == str:
            cmd_str = self.command
        else:
            cmd_str = self.command.to_dtmf()

        return f'{self.root} {self.macro_name} {cmd_str}'

    def apply(self, config: ConfigAcc) -> None:
        if self.macro_name in config.macros:
            # TODO: better exception type
            raise ValueError(f"Macro name {self.macro_name} already in use!")

        config.macros[self.macro_name] = [self.command]


@dataclass
class EraseMacro(SCOMCommand):
    root = '21'
    parser = Group(Suppress(root) + FULL_MACRO_NAME('macro_name'))

    macro_name: str

    def to_dtmf(self):
        return f'{self.root} {self.macro_name}'

    def apply(self, config: ConfigAcc) -> None:
        if self.macro_name in config.macros:
            del config.macros[self.macro_name]


@dataclass
class EraseAllMacros(SCOMCommand):
    root = '22'
    parser = Group(Suppress(root) + Suppress('00'))

    def to_dtmf(self):
        return f'{self.root} 00'

    def apply(self, config: ConfigAcc) -> None:
        config.macros.clear()


@dataclass
class RemoveLastCommandFromMacro(SCOMCommand):
    root = '24'
    parser = Group(Suppress(root) + FULL_MACRO_NAME('macro_name'))

    macro_name: str

    def to_dtmf(self):
        return f'{self.root} {self.macro_name}'

    def apply(self, config: ConfigAcc) -> None:
        config.macros[self.macro_name].pop()



@dataclass
class SetClockAndCalendar(SCOMCommand):
    # TODO: fix bounds checking
    root = '25'
    parser = Group(Suppress(root) +
                   Integer(99, exact_chars=2)('year') +
                   Integer(12, exact_chars=2)('month') +
                   Integer(31, exact_chars=2)('day_of_month') +
                   Integer(6, exact_chars=1)('day_of_week') +
                   Integer(23, exact_chars=2)('hour') +
                   Integer(59, exact_chars=2)('minute') +
                   Integer(59, exact_chars=2)('second'))

    year: int
    month: int
    day_of_month: int
    day_of_week: int
    hour: int
    minute: int
    second: int

    def to_dtmf(self):
        return f'{self.root} {self.year:02} {self.month:02} {self.day_of_month:02} {self.day_of_week} {self.hour:02} {self.minute:02} {self.second:02}'


@dataclass
class SetEventTriggeredMacro(SCOMCommand):
    root = '26'
    parser = Group(Suppress(root) +
                   Suppress('0') + Char('0123')('port') + NumWord(2)('event_macro_number') +
                   FULL_MACRO_NAME('macro_name')[0, 1])

    port: str
    event_macro_number: str
    macro_name: Optional[str] = None

    def to_dtmf(self):
        return f'{self.root} 0{self.port}{self.event_macro_number} {self.macro_name or ""}'


@dataclass
class RenameMacro(SCOMCommand):
    root = '27'
    parser = Group(Suppress(root) + FULL_MACRO_NAME('old_name') + FULL_MACRO_NAME('new_name'))

    old_name: str
    new_name: str

    def to_dtmf(self):
        return f'{self.root} {self.old_name} {self.new_name}'

    def apply(self, config: ConfigAcc) -> None:
        config.macros[self.new_name] = config.macros[self.old_name]
        del config.macros[self.old_name]


@dataclass
class CreateSetpoint(SCOMCommand):
    # TODO: fix bounds checking
    root = '28'
    parser = Group(Suppress(root) +
                   NumWord(2)('setpoint_number') +
                   MACRO_NAME('macro') +
                   NumWord(2)('month') +
                   NumWord(2)('day') +
                   NumWord(2)('hour') +
                   NumWord(2)('minute'))

    setpoint_number: str
    macro: str
    month: str
    day: str
    hour: str
    minute: str

    def to_dtmf(self):
        return f'{self.root} {self.setpoint_number} {self.macro} {self.month:0>2} {self.day:0>2} {self.hour:0>2} {self.minute:0>2}'


@dataclass
class EnableDisableSetpoint(SCOMCommand):
    root = '28'
    parser = Group(Suppress(root) +
                   NumWord(2)('setpoint_number_start') +
                   NumWord(2)('setpoint_number_end')[0, 1] +
                   BOOLEAN('enabled'))

    setpoint_number_start: str
    enabled: str
    setpoint_number_end: Optional[str] = None

    def to_dtmf(self):
        if self.setpoint_number_end:
            return f'{self.root} {self.setpoint_number_start} {self.setpoint_number_end} {self.enabled}'
        else:
            return f'{self.root} {self.setpoint_number_start} {self.enabled}'


@dataclass
class AppendToMacro(SCOMCommand):
    root = '29'
    parser = Group(Suppress(root) + FULL_MACRO_NAME('macro_name') + CMD_OR_MACRO('command'))

    macro_name: str
    command: Union[PasswordAndCommand, str]

    def to_dtmf(self):
        if type(self.command) == str:
            cmd_str = self.command
        else:
            cmd_str = self.command.to_dtmf()
        return f'{self.root} {self.macro_name} {cmd_str}'

    def apply(self, config: ConfigAcc) -> None:
        config.macros[self.macro_name].append(self.command)


@dataclass
class SelectMessage(SCOMCommand):
    root = '31'
    parser = Group(Suppress(root) + NumWord(4)('message_number') + MESSAGE('message_contents')[0, 1])

    message_number: str
    message_contents: Optional[str] = None

    def to_dtmf(self):
        return f'{self.root} {self.message_number} {" ".join(self.message_contents)}'


@dataclass
class ListMacroInCW(SCOMCommand):
    root = '33'
    parser = Group(Suppress(root) + FULL_MACRO_NAME('macro_name'))

    macro_name: str

    def to_dtmf(self):
        return f'{self.root} {self.macro_name}'


@dataclass
class ReviewMessage(SCOMCommand):
    root = '34'
    parser = Group(Suppress(root) + NumWord(4)('message_number'))

    message_number: str

    def to_dtmf(self):
        return f'{self.root} {self.message_number}'


@dataclass
class ListMacroInSpeech(SCOMCommand):
    root = '35'
    parser = Group(Suppress(root) + FULL_MACRO_NAME('macro_name'))

    macro_name: str

    def to_dtmf(self):
        return f'{self.root} {self.macro_name}'


@dataclass
class ReadBack(SCOMCommand):
    # TODO
    root = '37'
    parser = Group(Suppress(root) + NumWord(2)('data_type') +
                   Char('012')('timer') +
                   Char('123')('port') +
                   NumWord(2)('timer_number'))


# @dataclass
# class ReadBackTimer(SCOMCommand):
#     root = '37'
#     parser = Group(Suppress(root) + Suppress('00') +
#                    Char('012')('timer') +
#                    Char('123')('port') +
#                    NumWord(2)('timer_number'))

#     timer: int
#     port: int
#     timer_number: int

#     def to_dtmf(self):
#         return f'{self.root} 00 {self.timer}{self.port}{self.timer_number}'


@dataclass
class SetCounterReloadValue(SCOMCommand):
    root = '45'
    parser = Group(Suppress(root) + COUNTER_NUMBER + UINT16('value'))

    port: str
    counter: str
    value: int

    def to_dtmf(self):
        return f'{self.root} 0{self.port}{self.counter} {self.value}'


@dataclass
class SetLongNamesEnabled(SCOMCommand):
    root = '46'
    parser = Group(Suppress(root) +
                   Combine('0' + Char(nums))('name_number') +
                   Suppress('00') +
                   BOOLEAN('state'))

    name_number: str
    state: str

    def to_dtmf(self):
        return f'{self.root} {self.name_number} 00 {self.state}'


@dataclass
class SetLongName(SCOMCommand):
    root = '46'
    parser = Group(Suppress(root) +
                   Combine('0' + Char(nums))('name_number') +
                   Suppress('01') +
                   Word(DTMF_CHARS, max=8)('name'))

    name_number: str
    state: str
    name: Optional[str] = None

    def to_dtmf(self):
        return f'{self.root} {self.name_number} 01 {self.name}'


@dataclass
class SetLongNameMacro(SCOMCommand):
    root = '46'
    parser = Group(Suppress(root) +
                   Combine('0' + Char(nums))('name_number') +
                   Suppress('02') +
                   FULL_MACRO_NAME('macro_name')[0, 1])

    name_number: str
    macro_name: Optional[str] = None

    def to_dtmf(self):
        return f'{self.root} {self.name_number} 02 {self.macro_name}'


@dataclass
class SetLongNamePortAccess(SCOMCommand):
    root = '46'
    parser = Group(Suppress(root) +
                   Combine('0' + Char(nums))('name_number') +
                   Suppress('03') +
                   Char('123')('ports')[0, 3])

    name_number: str
    ports: Iterable[str]

    def to_dtmf(self):
        return f'{self.root} {self.name_number} 03 {"".join(self.ports)}'


@dataclass
class AdjustDaylightSavingTime(SCOMCommand):
    root = '48'
    parser = Group(Suppress(root) + Char('012')('operation'))

    operation: str

    def to_dtmf(self):
        return f'{self.root} {self.operation}'


@dataclass
class SelectTimerTimeoutValue(SCOMCommand):
    root = '49'
    parser = Group(Suppress(root) + USER_TIMER('timer') + Suppress('03') + UINT16('delay'))

    timer: int
    delay: int

    def to_dtmf(self):
        return f'{self.root} {self.timer:02} 03 {self.delay}'


@dataclass
class SelectTimerEventMacro(SCOMCommand):
    root = '49'
    parser = Group(Suppress(root) + USER_TIMER('timer') + Suppress('02') + FULL_MACRO_NAME('macro')[0, 1])

    timer: int
    macro: Optional[str] = None

    def to_dtmf(self):
        return f'{self.root} {self.timer:02} 02 {self.macro}'


@dataclass
class StopTimer(SCOMCommand):
    root = '49'
    parser = Group(Suppress(root) + USER_TIMER('timer') + Suppress('00'))

    timer: int

    def to_dtmf(self):
        return f'{self.root} {self.timer:02} 00'


@dataclass
class StartTimerRetriggerable(SCOMCommand):
    root = '49'
    parser = Group(Suppress(root) + USER_TIMER('timer') + Suppress('01'))

    timer: int

    def to_dtmf(self):
        return f'{self.root} {self.timer:02} 01'


@dataclass
class StartTimerOneShot(SCOMCommand):
    root = '49'
    parser = Group(Suppress(root) + USER_TIMER('timer') + Suppress('04'))

    timer: int

    def to_dtmf(self):
        return f'{self.root} {self.timer:02} 04'


@dataclass
class SelectIDTailMessages(SCOMCommand):
    root = '50'
    parser = Group(Suppress(root) +
                   Suppress('0') + Char('012345')('message') +
                   NumWord(4)('message_number')[0, 1])

    message: str
    message_number: Optional[str] = None

    def to_dtmf(self):
        return f'{self.root} 0{self.message} {self.message_number or ""}'


@dataclass
class SelectDTMFDecoderAccessMode(SCOMCommand):
    root = '57'
    parser = Group(Suppress(root) + Char('123')('receiver') + Char('0123456')('mode'))

    receiver: str
    mode: str

    def to_dtmf(self):
        return f'{self.root} {self.reciever} {self.mode}'


@dataclass
class SelectPathAccessMode(SCOMCommand):
    root = '57'
    parser = Group(Suppress(root) +
                   Char('123')('receiver') +
                   Char('123')('transmitter') +
                   Char('0123456')('mode'))

    receiver: str
    transmitter: str
    mode: str

    def to_dtmf(self):
        return f'{self.root} {self.receiver}{self.transmitter} {self.mode}'


@dataclass
class SetSoftwareSwitch(SCOMCommand):
    root = '63'
    parser = Group(Suppress(root) + NumWord(4)('software_switch') + BOOLEAN('state'))

    software_switch: str
    state: str

    def to_dtmf(self):
        return f'{self.root} {self.software_switch} {self.state}'


@dataclass
class SelectLogicOutputsLatchedON(SCOMCommand):
    # TODO: bounds checking
    root = '70'
    parser = Group(Suppress(root) + Integer(11, exact_chars=2)('output*')[1, ...])

    output: Iterable[int]

    def to_dtmf(self):
        return f'{self.root} {" ".join(str(o).zfill(2) for o in self.output)}'


@dataclass
class SelectLogicOutputsLatchedOFF(SCOMCommand):
    # TODO: bounds checking
    root = '71'
    parser = Group(Suppress(root) + Integer(11, exact_chars=2)('output*')[1, ...])

    output: Iterable[int]

    def to_dtmf(self):
        return f'{self.root} {" ".join(str(o).zfill(2) for o in self.output)}'


@dataclass
class SelectLogicOutputsMomentaryON(SCOMCommand):
    # TODO: bounds checking
    root = '72'
    parser = Group(Suppress(root) + Integer(11, exact_chars=2)('output*')[1, ...])

    output: Iterable[int]

    def to_dtmf(self):
        return f'{self.root} {" ".join(str(o).zfill(2) for o in self.output)}'


@dataclass
class SelectLogicOutputsMomentaryOFF(SCOMCommand):
    # TODO: bounds checking
    root = '73'
    parser = Group(Suppress(root) + Integer(11, exact_chars=2)('output*')[1, ...])

    output: Iterable[int]

    def to_dtmf(self):
        return f'{self.root} {" ".join(str(o).zfill(2) for o in self.output)}'


@dataclass
class ControlTransmitterToneGenerator(SCOMCommand):
    # TODO: bounds checking
    root = '79'
    parser = Group(Suppress(root) +
                   Char('123')('transmitter') +
                   Suppress('0') + Integer(3, exact_chars=1)('mode') +
                   Integer(98, exact_chars=2)('message_level') +
                   NumWord(4)('tone_code'))

    transmitter: str
    mode: int
    message_level: int
    tone_code: str

    def to_dtmf(self):
        return f'{self.root} {" ".join(str(o).zfill(2) for o in self.output)}'


@dataclass
class IfThenElse(SCOMCommand):
    root = '76'
    parser = Group(Suppress(root) +
                   Suppress('0') + VALUE_TYPE('value_type') +
                   NumWord(4)('value') +
                   FULL_MACRO_NAME('true_macro') +
                   FULL_MACRO_NAME('false_macro')[0, 1])

    value_type: ValueType
    value: str
    true_macro: str
    false_macro: Optional[str] = None

    def to_dtmf(self):
        out = f'76 0{self.value_type.value} {self.value} {self.true_macro}'
        if self.false_macro is not None:
            out += ' ' + self.false_macro
        return out


@dataclass
class SelectPathPriority(SCOMCommand):
    root = '90'
    parser = Group(Suppress(root) + Char('123')('transmitter') + Char('123')('recievers*')[0, 3])

    transmitter: str
    recievers: Iterable[str] = ()

    def to_dtmf(self):
        return f'{self.root} {self.transmitter} {" ".join(self.recievers)}'


@dataclass
class AssignControlOperatorPassword(SCOMCommand):
    root = '92'
    parser = Group(Suppress(root) + PASSWD('new_password'))

    new_password: str

    def to_dtmf(self):
        return f'{self.root} {self.new_password}'


@dataclass
class AssignMasterPassword(SCOMCommand):
    root = '93'
    parser = Group(Suppress(root) + PASSWD('new_password'))

    new_password: str

    def to_dtmf(self):
        return f'{self.root} {self.new_password}'


@dataclass
class AssignControlOperatorPrivilegeLevel(SCOMCommand):
    root = '94'
    parser = Group(Suppress(root) +
                   ROOT_NUMBER('root_number') +
                   ROOT_NUMBER('root_number_end')[0, 1] +
                   BOOLEAN('privilege_level'))

    root_number: str
    privilege_level: str
    root_number_end: Optional[str] = None

    def to_dtmf(self):
        if self.root_number_end is None:
            return f'{self.root} {self.root_number} {self.privilege_level}'
        else:
            return f'{self.root} {self.root_number}{self.root_number_end} {self.privilege_level}'


@dataclass
class ResetConsoleDefaults(SCOMCommand):
    root = '95'
    parser = Group(Suppress(root) + Suppress('30'))

    def to_dtmf(self):
        return f'{self.root} 30'


@dataclass
class ControllerWarmStart(SCOMCommand):
    root = '95'
    parser = Group(Suppress(root) + Suppress('00'))

    def to_dtmf(self):
        return f'{self.root} 00'


@dataclass
class ControllerPowerCycle(SCOMCommand):
    root = '95'
    parser = Group(Suppress(root) + Suppress('42'))

    def to_dtmf(self):
        return f'{self.root} 42'


@dataclass
class Pause(SCOMCommand):
    root = '98'
    parser = Group(Suppress(root) + Suppress('0') + UINT16('seconds'))

    seconds: int

    def to_dtmf(self):
        return f'{self.root} 0 {self.seconds}'


@dataclass
class CancelPause(SCOMCommand):
    root = '98'
    parser = Group(Suppress(root) + Suppress('1') + Char('1239')('port'))

    port: str

    def to_dtmf(self):
        return f'{self.root} 1 {self.port}'

COMMAND <<= ungroup(Or([command.get_parser() for command in SCOMCommand.__subclasses__()])) \
    .setName('Command')

LINE = PASSWD_AND_COMMAND('password_and_command') + Suppress('*') + \
    (Suppress(';') + restOfLine('comment'))[0, 1]


def parse(string):
    print(f"original: {string.strip():<100}", end='')
    result = LINE.parseString(string, parseAll=True)
    print(result['password_and_command'])
    command = result['password_and_command'].command
    #print(result.asXML())
    print("back to dtmf:", command.to_dtmf())
    print(COMMAND.parseString(command.to_dtmf()))

    return result


if __name__ == '__main__':
    print()
    with (open("../../SCOM7330-Configs/FullConfigs/W1FN/Common.txt") as f,
          open("temp.txt", 'w') as out_f):
        lines = f.readlines()
        for line in lines[1:-1]:
            parse(line)
