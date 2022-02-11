from simulator import Signal, ArithmeticOperation, ArithmeticCombinator

import pytest
import numpy


numpy.seterr(all='ignore')


def test_add_single_single():
    c = ArithmeticCombinator('a', 'b', 'c', ArithmeticOperation.ADD)
    c.red_in.set('a', 1)
    c.red_in.set('b', 10)
    c.green_in.set('b', 100)
    c.green_in.set('c', 1000)
    c.tick()
    assert {'c': 111} == c.red_out.values
    assert {'c': 111} == c.green_out.values

def test_add_single_single_constant():
    c = ArithmeticCombinator('a', 10, 'c', ArithmeticOperation.ADD)
    c.red_in.set('a', 1)
    c.tick()
    assert {'c': 11} == c.red_out.values

def test_add_overflow():
    c = ArithmeticCombinator('a', 0x7fffffff, 'b', ArithmeticOperation.ADD)
    c.red_in.set('a', 0x7fffffff)
    c.tick()
    assert {'b': -2} == c.red_out.values

def test_subtract_each_signal_constant():
    c = ArithmeticCombinator(Signal.EACH, 100, 'a', ArithmeticOperation.SUBTRACT)
    c.red_in.set('a', 1)
    c.red_in.set('b', 10)
    c.tick()
    assert {'a': -189} == c.red_out.values

def test_multiply_each_each_signal():
    c = ArithmeticCombinator(Signal.EACH, 'a', Signal.EACH, ArithmeticOperation.MULTIPLY)
    c.red_in.set('a', 3)
    c.red_in.set('b', 4)
    c.red_in.set('c', 5)
    c.tick()
    assert {'a': 9, 'b': 12, 'c': 15} == c.red_out.values

def test_no_all_any_allowed():
    with pytest.raises(TypeError):
        ArithmeticCombinator(Signal.EVERYTHING, 0, 'a', ArithmeticOperation.ADD)

    with pytest.raises(TypeError):
        ArithmeticCombinator('a', 0, Signal.ANYTHING, ArithmeticOperation.ADD)

def test_no_virtual_right_allowed():
    with pytest.raises(TypeError):
        ArithmeticCombinator('a', Signal.EACH, 'a', ArithmeticOperation.ADD)

def test_no_each_with_single_left():
    with pytest.raises(TypeError):
        ArithmeticCombinator('a', 0, Signal.EACH, ArithmeticOperation.ADD)
