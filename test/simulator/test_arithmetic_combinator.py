from simulator import ArithmeticCombinator, ArithmeticOperation, signals
from typing import Dict
from utils import AnyInt

import pytest

def run(c: ArithmeticCombinator, inputs: Dict[str, AnyInt], outputs: Dict[str, AnyInt], debug: bool = False):
    if debug: print('\ninputs', inputs, 'outputs', outputs)
    c.red_in.network_write(inputs)
    if debug: print(c)
    c.tick()
    if debug: print(c)
    assert c.red_out.network_read() == outputs


def test_add_single_single():
    run(
        ArithmeticCombinator('a', 'b', 'c', ArithmeticOperation.ADD),
        {'a': 1, 'b': 10, 'c': 100},
        {'c': 11}
    )

def test_add_single_single_constant():
    run(
        ArithmeticCombinator('a', 10, 'c', ArithmeticOperation.ADD),
        {'a': 1},
        {'c': 11}
    )

def test_subtract_each_signal_constant():
    run(
        ArithmeticCombinator(signals.EACH, 100, 'a', ArithmeticOperation.SUBTRACT),
        {'a': 1, 'b': 10},
        {'a': -189}
    )

def test_multiply_each_each_signal():
    run(
        ArithmeticCombinator(signals.EACH, 'a', signals.EACH, ArithmeticOperation.MULTIPLY),
        {'a': 3, 'b': 4, 'c': 5},
        {'a': 9, 'b': 12, 'c': 15}
    )

def test_no_everything_allowed():
    with pytest.raises(TypeError):
        ArithmeticCombinator(signals.EVERYTHING, 0, 'a', ArithmeticOperation.ADD)

def test_no_anything_allowed():
    with pytest.raises(TypeError):
        ArithmeticCombinator('a', 0, signals.ANYTHING, ArithmeticOperation.ADD)

def test_no_virtual_right_allowed():
    with pytest.raises(TypeError):
        ArithmeticCombinator('a', signals.EACH, 'a', ArithmeticOperation.ADD)

def test_no_each_with_single_left():
    with pytest.raises(TypeError):
        ArithmeticCombinator('a', 0, signals.EACH, ArithmeticOperation.ADD)
