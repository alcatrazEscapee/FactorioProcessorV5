from typing import Dict
from simulator import Port


class Entity:
    """ Base class for all simulated entities (decider, arithmetic, and constant combinators) """

    connections: Dict[int, Dict[str, Port]]  # Dict[port (1 or 2), Dict[color ('red' or 'green'), Signals]]
    key: str  # A string key representing this combinator. Used to identify it in test cases

    def tick(self):
        raise NotImplementedError

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return self.key


class PortEntity(Entity):

    def __init__(self, port_id: int, color: str, port: Port):
        self.connections = {port_id: {color: port}}
        self.key = '[ %s ]' % port

    def tick(self):
        pass
