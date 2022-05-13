from typing import List, Set, Dict, Tuple, Mapping
from simulator import Entity, Port, ReadPort, ArithmeticCombinator, ConstantCombinator, DeciderCombinator, signals

from numpy import int32
from networkx import Graph
from networkx.algorithms.components import connected_components

import re


class Model:
    """ The model of a collection of entities. Handles updating them in Factorio style ticks and provides builders for their network connections """

    def __init__(self):
        self.network: Graph = Graph()
        self.network_connections: List[Set[Port]] = []
        self.entities: Dict[int, Entity] = {}
        self.tick_count = 0

    def add_entity(self, entity_id: int, entity: Entity):
        self.entities[entity_id] = entity

    def add_connection(self, left_entity: int, left_port: int, left_color: str, right_entity: int, right_port: int, right_color: str, ignore_unknown_entities: bool = True):
        """ Adds a connection between two entities, using the given port IDs (1 = input, 2 = output), with the provided color.
        Note that this supports wires that cross colors, where in practice, that is not possible.
        """
        if left_entity in self.entities and right_entity in self.entities:
            left = self.entities[left_entity].connections[left_port][left_color]
            right = self.entities[right_entity].connections[right_port][right_color]
            self.network.add_edge(left, right)
        elif not ignore_unknown_entities:
            raise ValueError('No entity by id %d' % (right_entity if left_entity in self.entities else left_entity))

    def setup(self):
        self.network_connections = [p for p in connected_components(self.network)]

    def tick_until_stable(self) -> int:
        """ Ticks until a stable condition is reached (no network value changes)
        - Always performs at least one tick
        - Returns one less than the number of ticks executed - as the last tick was the one that had no effect and thus should not be counted
        - Constant combinators need at least one tick to propagate their values after being programmatically set that needs to run before this
        """
        count = -1
        network_prev = None
        network_current = self.tick_network()
        while network_prev != network_current:
            network_prev = network_current
            self.tick_entities()
            network_current = self.tick_network()
            count += 1
        return count

    def tick(self):
        self.tick_network()
        self.tick_entities()
        self.tick_network()

    def tick_network(self) -> Tuple[Mapping[str, int32], ...]:
        snapshot: List[Mapping[str, int32]] = []
        for group in self.network_connections:
            net = signals.union_iter(g.network_read() for g in group)
            snapshot.append(net)
            for s in group:
                s.network_write(net)
        return tuple(snapshot)

    def tick_entities(self):
        for e in self.entities.values():
            e.tick()

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return 'Model[\n  ' + '\n  '.join(str(e) for e in self.entities.values()) + '\n]'


class EntityBuilder:
    """ A builder for a combinator in a ModelBuilder, in order to specify input and output connections """

    def __init__(self, entity_id: int):
        self.input = PortBuilder(entity_id, 1)
        self.output = PortBuilder(entity_id, 2)

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return 'Entity{%d}' % self.input.entity_id


class PortBuilder:
    """ A builder for a single port on a combinator in a ModelBuilder, in order to specify connections """

    def __init__(self, entity_id: int, port_id: int):
        self.entity_id = entity_id
        self.port_id = port_id

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return 'Port{%s:%s}' % (self.entity_id, self.port_id)


class ModelBuilder:

    AC_PATTERN = re.compile(r'([A-Za-z0-9]+):=([A-Za-z0-9]+)(\+|-|/|\*|<<|>>|&|\||^|\*\*|%)([A-Za-z0-9]+)')
    DC_PATTERN = re.compile(r'([A-Za-z0-9]+)(=1|)if([A-Za-z0-9]+)(=|!=|<=|>=|<|>)([A-Za-z0-9]+)')

    def __init__(self):
        self.model = Model()
        self.entity_id = -1

    def cc(self, spec: str) -> PortBuilder:
        port = constants(spec)
        self.entity_id += 1
        self.model.add_entity(self.entity_id, ConstantCombinator(port, True))
        return PortBuilder(self.entity_id, 1)

    def ac(self, spec: str) -> EntityBuilder:
        spec = spec.replace(' ', '')
        g = ModelBuilder.AC_PATTERN.match(spec)

        assert g, 'Unrecognized spec: %s' % spec

        out, lhs, op, rhs = g.groups()
        lhs, rhs = or_int(lhs), or_int(rhs)
        op = ArithmeticCombinator.VALUES[op]

        self.entity_id += 1
        self.model.add_entity(self.entity_id, ArithmeticCombinator(lhs, rhs, out, op))
        return EntityBuilder(self.entity_id)

    def dc(self, spec: str) -> EntityBuilder:
        spec = spec.replace(' ', '')
        g = ModelBuilder.DC_PATTERN.match(spec)

        assert g, 'Unrecognized spec: %s' % spec

        out, eq1, lhs, op, rhs = g.groups()
        lhs, rhs = or_int(lhs), or_int(rhs)
        op = DeciderCombinator.VALUES[op]

        self.entity_id += 1
        self.model.add_entity(self.entity_id, DeciderCombinator(lhs, rhs, out, op, not eq1))
        return EntityBuilder(self.entity_id)

    def red(self, *ports: PortBuilder): self.wire('red', *ports)
    def green(self, *ports: PortBuilder): self.wire('green', *ports)

    def wire(self, color: str, *ports: PortBuilder):
        assert color in ('red', 'green'), 'Illegal color: %s' % repr(color)
        assert len(ports) >= 2, 'Requires at least two ports'

        for i in range(len(ports) - 1):
            lhs: PortBuilder = ports[i]
            rhs: PortBuilder = ports[i + 1]

            self.model.add_connection(lhs.entity_id, lhs.port_id, color, rhs.entity_id, rhs.port_id, color)

    def probe(self, color: str, port: PortBuilder, spec: str | None = None) -> ReadPort:
        if spec is None:  # Read-only probe
            probe = ReadPort()
        else:  # Constant probe
            probe = constants(spec)
        target = self.model.entities[port.entity_id].connections[port.port_id][color]
        self.model.network.add_edge(target, probe)
        return probe

    def build(self) -> Model:
        self.model.setup()
        return self.model


def or_int(s: str) -> int | str:
    return int(s) if s.isnumeric() else s

def constants(spec: str) -> Port:
    spec = spec.replace(' ', '')
    port = Port()
    pairs = tuple(s.split('=') for s in spec.split(','))

    for k, v in pairs:
        port[k] = int(v)

    return port
