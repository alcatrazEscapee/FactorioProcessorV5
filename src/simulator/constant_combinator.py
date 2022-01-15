from typing import List, Optional
from simulator import Signal, Entity


class ConstantCombinator(Entity):

    MAX_SIGNALS = 20

    def __init__(self, defined_signals: Signal, enabled: bool = True, signal_indexes: List[Optional[str]] = None):
        super().__init__()
        self.red = Signal()
        self.green = Signal()

        self.connections = {'1': {'red': self.red, 'green': self.green}}

        # Signal conditions
        if len(defined_signals.values) > ConstantCombinator.MAX_SIGNALS:
            raise TypeError('can only define [0, %d] signals, not %d' % (ConstantCombinator.MAX_SIGNALS, len(defined_signals.values)))
        if signal_indexes is None:
            signal_indexes = list(defined_signals.values.keys())

        self.defined_signals = defined_signals
        self.enabled = enabled
        self.signal_indexes = signal_indexes

    def tick(self):
        # Output all defined signals on both red and green channels
        if self.enabled:
            self.red.update(self.defined_signals)
            self.green.update(self.defined_signals)

    def __str__(self):
        return 'Constant: S = %s' % self.defined_signals
