from typing import List, Set, Dict, Optional, Union, TypeVar, Type, Any
from numpy import int32
from utils import Json, JsonObject
from simulator import Signal, Entity, ArithmeticOperation, DeciderOperation, ConstantCombinator, ArithmeticCombinator, DeciderCombinator

from networkx import Graph
from networkx.algorithms.components import connected_components

import blueprint


class Model:
    """ The model of a collection of entities. Handles updating them in Factorio style ticks and provides builders for their network connections """

    def __init__(self):
        self.network: Graph = Graph()
        self.network_connections: Optional[List[Set[Signal]]] = None
        self.network_current: List[Signal.Values] = []
        self.network_prev: List[Signal.Values] = []
        self.entities: Dict[int, Entity] = {}
        self.tick_count = 0

    def add_entity(self, entity_id: int, entity: Entity):
        self.entities[entity_id] = entity

    def add_connection(self, left_entity: int, left_port: int, left_color: str, right_entity: int, right_port: int, right_color: str):
        """ Ignores unknown entity id references """
        if left_entity in self.entities and right_entity in self.entities:
            left = self.entities[left_entity].connections[left_port][left_color]
            right = self.entities[right_entity].connections[right_port][right_color]
            self.network.add_edge(left, right)

    def setup(self):
        self.network_connections = [p for p in connected_components(self.network)]

    def tick_until_stable(self) -> int:
        """ Ticks until a stable condition is reached (no network value changes)
        - Always performs at least one tick
        - Returns one less than the number of ticks executed - as the last tick was the one that had no effect and thus should not be counted
        - Constant combinators need at least one tick to propagate their values after being programmatically set that needs to run before this
        """
        count = -1
        self.network_prev = None
        while self.network_prev != self.network_current:
            self.network_prev = self.network_snapshot()
            self.tick()
            self.network_current = self.network_snapshot()
            count += 1
        return count

    def tick(self):
        self.tick_network()
        self.tick_entities()

    def tick_network(self):
        for group in self.network_connections:
            # Set each network node to the sum of all signals in the group
            net = Signal.sum_of(group)
            for s in group:
                s.update(net)  # Update each individual signal with the current input values

    def tick_entities(self):
        # Tick all entities
        for e in self.entities.values():
            e.tick()

    def network_snapshot(self) -> List[Signal.Values]:
        return [Signal.sum_of(group).values for group in self.network_connections]

    def __str__(self):
        return 'EntityModel:\n :%s' % '\n :'.join(str(e) for e in self.entities.values())


E = TypeVar('E', bound=Entity)


class Simulator:

    def __init__(self, blueprint_string: str):
        bp = blueprint.decode_blueprint_string(blueprint_string)
        model = decode_model(bp)

        self.model = model
        self.model.setup()

    def find(self, key: str, cls: Type[E]) -> E:
        """
        Finds a combinator by a unique key describing it's signals
        Constant Combinators:
        - A string representing the alphanumeric signals, with rows seperated by a space. e.g. 'K CLK'
        Decider + Arithmetic Combinators:
        - A RTN style declaration such as A:=X+5
        """
        for c in self.model.entities.values():
            if c.key == key:
                assert isinstance(c, cls)
                return c
        raise ValueError('Combinator with key \'%s\' not found in model' % key)

    def tick(self, count: int = 1):
        for _ in range(count):
            self.model.tick()

    def tick_until_stable(self) -> int:
        self.model.tick()  # One tick for constant combinators to push their new values onto the network (not counted)
        return self.model.tick_until_stable()



def decode_model(json: JsonObject) -> Model:
    model = Model()
    bp = as_obj(json['blueprint'])
    entities = as_list(bp['entities'])

    # First pass, just create the entities
    for entity_data in entities:
        as_obj(entity_data)
        entity_id = as_int(entity_data['entity_number'])
        entity_type = as_str(entity_data['name'])
        try:
            if entity_type == 'decider-combinator':
                model.add_entity(entity_id, decode_decider_combinator(entity_data))
            elif entity_type == 'arithmetic-combinator':
                model.add_entity(entity_id, decode_arithmetic_combinator(entity_data))
            elif entity_type == 'constant-combinator':
                model.add_entity(entity_id, decode_constant_combinator(entity_data))
        except ValueError as e:
            raise ValueError('Problem decoding entity id %d, (%s): %s' % (entity_id, entity_type, e), e)

    # Second pass, initialize network connections
    for entity_data in entities:
        entity_type = as_str(entity_data['name'])
        if entity_type in COMBINATORS:
            decode_connections(model, entity_data)

    model.setup()
    return model


def decode_decider_combinator(entity_data: JsonObject) -> DeciderCombinator:
    control = as_obj(as_obj(entity_data['control_behavior'])['decider_conditions'])
    left = decode_signal(control['first_signal'])
    right = decode_signal_or_constant(control, 'second_signal', 'constant')
    operation = DECODE_DECIDER_OPERATORS[control['comparator']]
    out = decode_signal(control['output_signal'])
    output_input_count = as_bool(control['copy_count_from_input'])
    return DeciderCombinator(left, right, out, operation, output_input_count)

def decode_arithmetic_combinator(entity_data: JsonObject) -> ArithmeticCombinator:
    control = as_obj(as_obj(entity_data['control_behavior'])['arithmetic_conditions'])
    left = decode_signal_or_constant(control, 'first_signal', 'first_constant')
    right = decode_signal_or_constant(control, 'second_signal', 'second_constant')
    operation = DECODE_ARITHMETIC_OPERATORS[control['operation']]
    out = decode_signal(control['output_signal'])
    return ArithmeticCombinator(left, right, out, operation)

def decode_constant_combinator(entity_data: JsonObject) -> Entity:
    control = as_obj(entity_data['control_behavior'])
    filters = as_list(control['filters'])

    signals = Signal()
    signal_indexes: List[Optional[str]] = [None] * ConstantCombinator.MAX_SIGNALS
    for signal_data in filters:
        as_obj(signal_data)
        signal_id = decode_signal(signal_data['signal'])
        signal_value = int32(as_int(signal_data['count']))
        signal_index = as_int(signal_data['index'])
        signal_indexes[signal_index - 1] = signal_id
        signals.set(signal_id, signal_value)

    is_enabled = as_bool(or_else(control, 'is_on', True))
    return ConstantCombinator(signals, is_enabled, signal_indexes)


def decode_connections(model: Model, entity_data: JsonObject):
    if 'connections' in entity_data:
        connections = as_obj(entity_data['connections'])
        left_id = as_int(entity_data['entity_number'])
        for left_port in (1, 2):
            left_port_key = str(left_port)
            if left_port_key in connections:
                port_connections = as_obj(connections[left_port_key])
                for color in ('red', 'green'):
                    if color in port_connections:
                        color_connections = as_list(port_connections[color])
                        for edge in color_connections:
                            right_id = as_int(edge['entity_id'])
                            right_port = as_int(or_else(edge, 'circuit_id', 1))
                            model.add_connection(
                                left_id, left_port, color,
                                right_id, right_port, color
                            )


def decode_signal_or_constant(root_data: JsonObject, signal_name: str, constant_name: str) -> Union[str, int32]:
    # Expects either signal_name or constant_name to be contained in root_data, and processes accordingly
    if signal_name in root_data:
        return decode_signal(root_data[signal_name])
    else:
        return int32(root_data[constant_name])

def decode_signal(signal_data: Json) -> str:
    return as_str(as_obj(signal_data)['name'])


def as_obj(j: Json) -> JsonObject: return as_type(j, 'JsonObject', dict)
def as_list(j: Json) -> List[Json]: return as_type(j, 'List[Json]', list)
def as_int(j: Json) -> int: return as_type(j, 'int', int)
def as_str(j: Json) -> str: return as_type(j, 'str', str)
def as_bool(j: Json) -> bool: return as_type(j, 'bool', bool)

def as_type(j: Json, j_name: str, j_type) -> Any:
    assert isinstance(j, j_type), 'Not a %s: %s' % (j_name, repr(j))
    return j

def or_else(j: JsonObject, key: str, default_value: Any) -> Any:
    return j[key] if key in j else default_value


COMBINATORS = {'decider-combinator', 'arithmetic-combinator', 'constant-combinator'}
DECODE_ARITHMETIC_OPERATORS = {
    '+': ArithmeticOperation.ADD,
    '-': ArithmeticOperation.SUBTRACT,
    '*': ArithmeticOperation.MULTIPLY,
    '/': ArithmeticOperation.DIVIDE,
    '%': ArithmeticOperation.MODULO,
    '^': ArithmeticOperation.EXPONENT,
    '<<': ArithmeticOperation.LEFT_SHIFT,
    '>>': ArithmeticOperation.RIGHT_SHIFT,
    'AND': ArithmeticOperation.AND,
    'OR': ArithmeticOperation.OR,
    'XOR': ArithmeticOperation.XOR
}
DECODE_DECIDER_OPERATORS = {
    '<': DeciderOperation.LESS_THAN,
    '>': DeciderOperation.GREATER_THAN,
    '<=': DeciderOperation.LESS_EQUAL,
    '≥': DeciderOperation.GREATER_EQUAL,
    '=': DeciderOperation.EQUAL,
    '≠': DeciderOperation.NOT_EQUAL
}