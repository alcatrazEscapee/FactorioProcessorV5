from typing import List, Optional
from simulator import Port, Entity


class ConstantCombinator(Entity):
    """
    Functional model of a Constant Combinator in Factorio
    """

    MAX_SIGNALS = 20

    def __init__(self, constants: Port, enabled: bool = True):
        super().__init__()
        self.red = Port()
        self.green = Port()

        self.constants = constants
        self.enabled = enabled
        self.connections = {1: {'red': self.red, 'green': self.green}}
        self.key = str(self.constants)

    def tick(self):
        # Output all defined signals on both red and green channels
        if self.enabled:
            self.red.write(self.constants.signals)
            self.green.write(self.constants.signals)
        else:
            self.red.clear()
            self.green.clear()

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return '[%s <- %s]' % (self.green, self.constants)
