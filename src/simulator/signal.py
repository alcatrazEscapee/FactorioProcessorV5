from typing import Dict, Optional, Sequence
from collections import defaultdict
from numpy import int32
from utils import AnyInt, AnyValue


class Signal:
    """ A collection or bus of individual signals, each consisting of a id and integer value. """

    # Virtual Signals
    EACH = 'each'
    ANYTHING = 'anything'
    EVERYTHING = 'everything'

    Values = Dict[str, int32]

    @staticmethod
    def is_named(value: AnyValue) -> bool:
        return isinstance(value, str)

    @staticmethod
    def is_virtual(signal: str) -> bool:
        return signal == Signal.EACH or signal == Signal.ANYTHING or signal == Signal.EVERYTHING

    @staticmethod
    def to_formal(letter: str) -> str:
        return 'signal-' + letter.upper()

    @staticmethod
    def from_formal(signal: Optional[str]) -> Optional[str]:
        return signal[-1].lower() if signal is not None and signal.startswith('signal-') else ''

    @staticmethod
    def sum_of(signals: Sequence['Signal']) -> 'Signal':
        s = Signal()
        for s0 in signals:
            s += s0
        return s

    def __init__(self):
        self.values: Signal.Values = defaultdict(int32)

    def set(self, signal_name: str, signal_value: AnyInt):
        self.values[signal_name] = int32(signal_value)

    def get(self, signal_name: str, default: Optional[AnyInt] = 0) -> Optional[int32]:
        if signal_name in self.values:
            return self.values[signal_name]
        if default is not None:
            return int32(default)
        return None

    def update(self, other: 'Signal'):
        # Sets this signal to match the other
        self.clear()
        for key, val in other.values.items():
            self.values[key] = val

    def clear(self):
        # Clears all signal values
        self.values.clear()

    def __add__(self, other: 'Signal') -> 'Signal':
        if not isinstance(other, Signal):
            raise TypeError('Incompatible types for signal addition: %s and %s' % (str(self), str(other)))
        new = Signal()
        for key, val in self.values.items():
            new.values[key] += val
        for key, val in other.values.items():
            new.values[key] += val
        return new

    def __str__(self) -> str:
        return dict.__repr__(self.values)  # call dict repr in order to skip the type output
