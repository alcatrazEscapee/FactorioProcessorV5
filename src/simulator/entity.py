from typing import Dict
from simulator import Signal


class Entity:
    """ Base class for all simulated entities (decider, arithmetic, and constant combinators) """

    def __init__(self, x: int = 0, y: int = 0, direction: int = 1):
        self.x = x
        self.y = y
        self.direction = direction
        self.connections: Dict[str, Dict[str, Signal]] = {}  # Dict[port ('1' or '2'), Dict[color ('red' or 'green'), Signals]]

    def set_placement_data(self, x: int, y: int, direction: int) -> 'Entity':
        self.x = x
        self.y = y
        self.direction = direction
        return self

    def tick(self):
        raise NotImplementedError

    # Connection accessor, used by protocol to set connections from json
    def get_signal(self, port: str, color: str) -> Signal:
        return self.connections[str(port)][str(color)]
