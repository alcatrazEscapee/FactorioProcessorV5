from simulator import DeciderOperation, DeciderCombinator, signals
from typing import Dict
from utils import AnyInt


def run(c: DeciderCombinator, inputs: Dict[str, AnyInt], outputs: Dict[str, AnyInt], debug: bool = False):
    if debug: print('\ninputs', inputs, 'outputs', outputs)
    c.red_in.network_write(inputs)
    if debug: print(c)
    c.tick()
    if debug: print(c)
    assert c.red_out.network_read() == outputs


def test_single_single_output_1():
    run(
        DeciderCombinator('a', 'b', 'c', DeciderOperation.EQUAL, False),
        {'a': 123, 'b': 123},
        {'c': 1}
    )

def test_single_single_output_input():
    run(
        DeciderCombinator('a', 'b', 'a', DeciderOperation.EQUAL, True),
        {'a': 123, 'b': 123},
        {'a': 123}
    )

def test_each_each_output_1():
    run(
        DeciderCombinator(signals.EACH, 5, signals.EACH, DeciderOperation.GREATER_THAN),
        {'a': 4, 'b': 5, 'c': 6},
        {'c': 1}
    )

def test_each_each_output_input():
    run(
        DeciderCombinator(signals.EACH, 5, signals.EACH, DeciderOperation.GREATER_EQUAL, True),
        {'a': 4, 'b': 5, 'c': 6},
        {'b': 5, 'c': 6}
    )

def test_each_single_output_1():
    run(
        DeciderCombinator(signals.EACH, 123, 'a', DeciderOperation.NOT_EQUAL),
        {'a': 345, 'b': 123, 'c': 234},
        {'a': 2}
    )

def test_each_single_output_input():
    run(
        DeciderCombinator(signals.EACH, 10, 'a', DeciderOperation.NOT_EQUAL, True),
        {'a': 1, 'b': 10, 'c': 100},
        {'a': 101}
    )

def test_everything_pass_empty_inputs():
    run(
        DeciderCombinator(signals.EVERYTHING, 123, 'a', DeciderOperation.EQUAL),
        {},
        {'a': 1}
    )

def test_anything_fail_empty_inputs():
    run(
        DeciderCombinator(signals.ANYTHING, 123, 'a', DeciderOperation.EQUAL),
        {},
        {}
    )

def test_everything_signal_pass():
    run(
        DeciderCombinator(signals.EVERYTHING, 10, 'a', DeciderOperation.EQUAL),
        {'a': 10, 'b': 10},
        {'a': 1}
    )

def test_everything_signal_fail():
    run(
        DeciderCombinator(signals.EVERYTHING, 10, 'a', DeciderOperation.NOT_EQUAL),
        {'a': 10, 'b': 101},
        {}
    )

def test_anything_everything_pass():
    run(
        DeciderCombinator(signals.ANYTHING, 10, signals.EVERYTHING, DeciderOperation.EQUAL),
        {'a': 10, 'b': 100},
        {'a': 1, 'b': 1}
    )

def test_anything_everything_fail():
    run(
        DeciderCombinator(signals.ANYTHING, 10, signals.EVERYTHING, DeciderOperation.EQUAL),
        {'a': 1, 'b': 100},
        {}
    )
