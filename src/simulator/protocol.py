# Protocol for json - model encoding

from typing import Dict, Any, TypeVar, Union, Tuple, List, Optional
from numpy import int32
from simulator import Model, Entity, Signal, DeciderCombinator, ArithmeticCombinator, ConstantCombinator, DeciderOperation, ArithmeticOperation

K = TypeVar('K')
V = TypeVar('V')


def decode_model(json: Dict[str, Any]) -> Model:
    model = Model()
    entities = json['blueprint']['entities']
    # First pass, just create the entities
    for entity_data in entities:
        entity_id = entity_data['entity_number']
        entity_type = entity_data['name']
        try:
            if entity_type == 'decider-combinator':
                model.add_entity(decode_decider_combinator(entity_data))
            elif entity_type == 'arithmetic-combinator':
                model.add_entity(decode_arithmetic_combinator(entity_data))
            elif entity_type == 'constant-combinator':
                model.add_entity(decode_constant_combinator(entity_data))
        except ValueError as e:
            raise ValueError('Problem decoding entity id %d, (%s): %s' % (entity_id, entity_type, e), e)
    # Second pass, initialize network connections
    for entity_data in entities:
        if entity_data['name'] in COMBINATORS:
            decode_connections(model, entity_data)
    return model


def decode_decider_combinator(entity_data: Dict[str, Any]) -> Entity:
    control = entity_data['control_behavior']['decider_conditions']
    left = decode_signal(get_or(control, 'first_signal', err='Missing first_signal'))
    right = decode_signal_or_constant(control, 'second_signal', 'constant')
    operation = DECODE_DECIDER_OPERATORS[get_or(control, 'comparator', err='Missing comparator')]
    out = decode_signal(get_or(control, 'output_signal', err='Missing output_signal'))
    output_input_count = bool(get_or(control, 'copy_count_from_input', err='Missing copy_count_from_input'))
    return DeciderCombinator(left, right, out, operation, output_input_count).set_placement_data(*decode_placement_data(entity_data))


def decode_arithmetic_combinator(entity_data: Dict[str, Any]) -> Entity:
    control = entity_data['control_behavior']['arithmetic_conditions']
    left = decode_signal_or_constant(control, 'first_signal', 'first_constant')
    right = decode_signal_or_constant(control, 'second_signal', 'second_constant')
    operation = DECODE_ARITHMETIC_OPERATORS[control['operation']]
    out = decode_signal(control['output_signal'])
    return ArithmeticCombinator(left, right, out, operation).set_placement_data(*decode_placement_data(entity_data))


def decode_constant_combinator(entity_data: Dict[str, Any]) -> Entity:
    control = get_or(entity_data, 'control_behavior', {})
    filters = get_or(control, 'filters', [])
    signals = Signal()
    signal_indexes: List[Optional[str]] = [None] * ConstantCombinator.MAX_SIGNALS
    for signal_data in filters:
        signal_id = decode_signal(get_or(signal_data, 'signal', err='Missing signal'))
        signal_value = int32(get_or(signal_data, 'count', err='Missing count'))
        signal_index: int = int(get_or(signal_data, 'index', err='Missing index'))
        signal_indexes[signal_index - 1] = signal_id
        signals.set(signal_id, signal_value)
    is_enabled = get_or(control, 'is_on', True)

    # Check if this is a special waveform combinator, indicated by the presence of SIGNAL_DOT in the last position
    return ConstantCombinator(signals, is_enabled, signal_indexes).set_placement_data(*decode_placement_data(entity_data))


def decode_connections(model: Model, entity_data: Dict[str, Any]):
    connections = get_or(entity_data, 'connections')
    if connections is not None:
        left_id = entity_data['entity_number']
        for left_port in ('1', '2'):
            port_connections = get_or(connections, left_port)
            if port_connections is not None:
                for color in ('red', 'green'):
                    color_connections = get_or(port_connections, color)
                    if color_connections is not None:
                        for edge in color_connections:
                            right_id = edge['entity_id']
                            right_port = get_or(edge, 'circuit_id', '1')
                            model.add_connection(model.get_entity(left_id).get_signal(left_port, color), model.get_entity(right_id).get_signal(right_port, color))


def decode_signal_or_constant(root_data: Dict[str, Any], signal_name: str, constant_name: str) -> Union[str, int32]:
    # Expects either signal_name or constant_name to be contained in root_data, and processes accordingly
    signal_data = get_or(root_data, signal_name)
    if signal_data is not None:
        return decode_signal(signal_data)
    else:
        return int32(root_data[constant_name])


def decode_signal(signal_data: Dict[str, Any]) -> str:
    return str(signal_data['name'])


def decode_placement_data(entity_data: Dict[str, Any]) -> Tuple[int, int, int]:
    position = get_or(entity_data, 'position', err='Missing position')
    x = int(get_or(position, 'x', err='Missing x value'))
    y = int(get_or(position, 'y', err='Missing y value'))
    direction = int(get_or(entity_data, 'direction', err='Missing direction'))
    return x, y, direction


def get_or(dictionary: Dict[K, V], key: K, default: V = None, err: str = None) -> V:
    if key in dictionary:
        return dictionary[key]
    else:
        if err is not None:
            raise ValueError(err)
        return default


def create_inverse_dict(dictionary: Dict[K, V]) -> Dict[V, K]:
    return dict((v, k) for k, v in dictionary.items())


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
ENCODE_ARITHMETIC_OPERATORS = create_inverse_dict(DECODE_ARITHMETIC_OPERATORS)
DECODE_DECIDER_OPERATORS = {
    '<': DeciderOperation.LESS_THAN,
    '>': DeciderOperation.GREATER_THAN,
    '<=': DeciderOperation.LESS_EQUAL,
    '>=': DeciderOperation.GREATER_EQUAL,
    '=': DeciderOperation.EQUAL,
    '!=': DeciderOperation.NOT_EQUAL
}
ENCODE_DECIDER_OPERATORS = create_inverse_dict(DECODE_DECIDER_OPERATORS)
