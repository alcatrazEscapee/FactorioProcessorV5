from typing import Dict, Iterable
from utils import AnyValue
from numpy import int32

EACH = 'each'
ANYTHING = 'anything'
EVERYTHING = 'everything'

Signals = Dict[str, int32]


def is_named(signal: AnyValue) -> bool:
    """ Return true if 'signal' is a name of a signal, not a constant """
    return isinstance(signal, str)

def is_virtual(signal: AnyValue) -> bool:
    """ Return true if 'signal' is a special named signal, one of EACH, EVERYTHING, or ANYTHING """
    return signal == EACH or signal == EVERYTHING or signal == ANYTHING

def format(values: Signals) -> str:
    """ Formats the values of a signal dictionary into a standard string """
    return '{' + ', '.join('%s=%d' % (k, v) for k, v in values.items()) + '}'

def union_iter(values: Iterable[Signals]) -> Signals:
    """ Takes the sum of an iterable of signal dictionaries and returns a new dictionary as the sum """
    result = {}
    for v in values:
        union_mutable(result, v)
    return result

def union(left: Signals, right: Signals) -> Signals:
    """ Takes the sum of two signal dictionaries and returns a new dictionary as the sum """
    result = {}
    union_mutable(result, left)
    union_mutable(result, right)
    return result

def union_mutable(left: Signals, right: Signals):
    for k, v in right.items():
        if k not in left:
            left[k] = v
        else:
            left[k] += v
