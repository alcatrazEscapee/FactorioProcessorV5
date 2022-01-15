from simulator import Signal, DeciderOperation, DeciderCombinator


def test_single_single_output_1():
    d = DeciderCombinator('a', 'b', 'c', DeciderOperation.EQUAL, False)
    d.red_in.set('a', 123)
    d.green_in.set('b', 123)
    d.tick()
    assert {'c': 1} == d.red_out.values

def test_single_single_output_input():
    d = DeciderCombinator('a', 'b', 'a', DeciderOperation.EQUAL, True)
    d.red_in.set('a', 123)
    d.green_in.set('b', 123)
    d.tick()
    assert {'a': 123} == d.red_out.values

def test_each_each_output_1():
    d = DeciderCombinator(Signal.EACH, 5, Signal.EACH, DeciderOperation.GREATER_THAN)
    d.red_in.set('a', 4)
    d.red_in.set('b', 5)
    d.red_in.set('c', 6)
    d.tick()
    assert {'c': 1} == d.red_out.values

def test_each_each_output_input():
    d = DeciderCombinator(Signal.EACH, 5, Signal.EACH, DeciderOperation.GREATER_EQUAL, True)
    d.red_in.set('a', 4)
    d.red_in.set('b', 5)
    d.red_in.set('c', 6)
    d.tick()
    assert {'b': 5, 'c': 6} == d.red_out.values

def test_each_single_output_1():
    d = DeciderCombinator(Signal.EACH, 123, 'a', DeciderOperation.NOT_EQUAL)
    d.red_in.set('a', 345)
    d.red_in.set('b', 123)
    d.red_in.set('c', 234)
    d.tick()
    assert {'a': 2} == d.red_out.values

def test_each_single_output_input():
    d = DeciderCombinator(Signal.EACH, 10, 'a', DeciderOperation.NOT_EQUAL, True)
    d.red_in.set('a', 1)
    d.red_in.set('b', 10)
    d.red_in.set('c', 100)
    d.tick()
    assert {'a': 101} == d.red_out.values

def test_everything_pass_empty_inputs():
    d = DeciderCombinator(Signal.EVERYTHING, 123, 'a', DeciderOperation.EQUAL)
    d.tick()
    assert {'a': 1} == d.red_out.values

def test_anything_fail_empty_inputs():
    d = DeciderCombinator(Signal.ANYTHING, 123, 'a', DeciderOperation.EQUAL)
    d.tick()
    assert {} == d.red_out.values

def test_everything_signal_pass():
    d = DeciderCombinator(Signal.EVERYTHING, 10, 'a', DeciderOperation.EQUAL)
    d.red_in.set('a', 10)
    d.red_in.set('b', 10)
    d.tick()
    assert {'a': 1} == d.red_out.values

def test_everything_signal_fail():
    d = DeciderCombinator(Signal.EVERYTHING, 10, 'a', DeciderOperation.NOT_EQUAL)
    d.red_in.set('a', 10)
    d.red_in.set('b', 101)
    d.tick()
    assert {} == d.red_out.values

def test_anything_everything_pass():
    d = DeciderCombinator(Signal.ANYTHING, 10, Signal.EVERYTHING, DeciderOperation.EQUAL)
    d.red_in.set('a', 10)
    d.red_in.set('b', 100)
    d.tick()
    assert {'a': 1, 'b': 1} == d.red_out.values

def test_anything_everything_fail():
    d = DeciderCombinator(Signal.ANYTHING, 10, Signal.EVERYTHING, DeciderOperation.EQUAL)
    d.red_in.set('a', 1)
    d.red_in.set('b', 100)
    d.tick()
    assert {} == d.red_out.values
