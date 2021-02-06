from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    CW = 0
    Single_Tone_Beep = 1
    Dual_Tone_Beep = 2
    Single_Tone_Page = 3
    Two_Tone_Page = 4
    Five_Six_Tone_Page = 5
    DTMF_Page = 6
    SELCAL_Page = 7
    Speech_Playback = 8


class ValueType(Enum):
    timers = 0
    software_switch = 3
    boolean = 4
    scheduler_setpoint_enable = 5
    user_timers = 6
