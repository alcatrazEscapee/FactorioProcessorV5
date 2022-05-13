from numpy import int32
from typing import Dict
from utils import AnyInt
from simulator import signals


class Port:
    """
    An abstraction which represents a node on the output of a combinator

    A port can have values written to it, which are then summed and propagated to the rest of the network
    In order to read from a network, it must be done from a connected 'ReadPort'
    """

    signals: Dict[str, int32]

    def __init__(self):
        self.signals = {}

    def clear(self):
        """ Clears this port's current values """
        self.signals = {}

    def __getitem__(self, item: str) -> int32:
        if item in self.signals:
            return self.signals[item]
        return int32(0)

    def __setitem__(self, key: str, value: AnyInt):
        self.signals[key] = int32(value)

    def network_read(self) -> Dict[str, int32]:
        """ Reads the signals from this port, that are pushed onto the network """
        return self.signals

    def network_write(self, signals: Dict[str, int32]):
        """ Writes the sum of the signals on the network to this port """
        pass

    def write(self, signals: Dict[str, int32]):
        """ Writes the signals to this port """
        self.signals = dict(signals)

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return signals.format(self.signals)


class ReadPort(Port):
    """
    A read only port which represents a node on the input of a combinator

    This port only allows values to be read to it, and values can be written from the combinator network
    As such, it will contain the sum of all values on the network, after each tick
    """

    def network_read(self) -> Dict[str, int32]:
        return {}

    def network_write(self, signals: Dict[str, int32]):
        self.signals = signals
