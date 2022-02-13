from typing import List, Optional
from simulator import Signal, Entity
from utils import AnyInt
from numpy import int32


class ConstantCombinator(Entity):

    MAX_SIGNALS = 20

    def __init__(self, defined_signals: Signal, enabled: bool = True, signal_indexes: List[Optional[str]] = None):
        super().__init__()
        self.red = Signal()
        self.green = Signal()

        self.red_view = Signal()
        self.green_view = Signal()

        self.connections = {1: {'red': self.red, 'green': self.green}}

        # Signal conditions
        if len(defined_signals.values) > ConstantCombinator.MAX_SIGNALS:
            raise TypeError('can only define [0, %d] signals, not %d' % (ConstantCombinator.MAX_SIGNALS, len(defined_signals.values)))
        if synthetic := (signal_indexes is None):
            signal_indexes = list(defined_signals.values.keys())

        self.defined_signals = defined_signals
        self.enabled = enabled
        self.signal_indexes = signal_indexes

        self.key = '<synthetic>' if synthetic else '%s %s' % (
            ''.join(Signal.from_formal(self.signal_indexes[i]) for i in range(10)),
            ''.join(Signal.from_formal(self.signal_indexes[i + 10]) for i in range(10)),
        )

    def tick(self):
        # Save the current inputs (this tick) to a special, non-exposed set of signals
        self.red_view.update(self.red)
        self.green_view.update(self.green)

        # Output all defined signals on both red and green channels
        if self.enabled:
            self.red.update(self.defined_signals)
            self.green.update(self.defined_signals)

    def set(self, signal: str, value: AnyInt):
        """ Updates this combinators defined signals. """
        self.defined_signals.set(Signal.to_formal(signal), value)

    def toggle(self, on: bool = None):
        """ Updates the state of this combinator 'on' state """
        if on is None:
            self.enabled = not self.enabled
        else:
            self.enabled = on

    def get(self, signal: str) -> int32:
        """ Get the signal currently on the combinators network connection. Note: this value is not visible in Factorio unless the same network is connected to a pole or other input. """
        return self.red_view.get(Signal.to_formal(signal)) + self.green_view.get(Signal.to_formal(signal))

    def __str__(self):
        return 'Constant: S = %s' % self.defined_signals
