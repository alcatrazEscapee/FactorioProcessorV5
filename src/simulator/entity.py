from typing import Dict
from simulator import Signal


class Entity:
    """ Base class for all simulated entities (decider, arithmetic, and constant combinators) """

    connections: Dict[int, Dict[str, Signal]]  # Dict[port (1 or 2), Dict[color ('red' or 'green'), Signals]]
    key: str  # A string key representing this combinator. Used to identify it in test cases

    def tick(self):
        raise NotImplementedError
