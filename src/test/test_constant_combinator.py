import pytest

import simulator.constant_combinator as cc
import simulator.signal as signal


def test_tick():
    s = signal.Signal()
    s.set('a', 123)
    c = cc.ConstantCombinator(s)
    c.tick()
    assert {'a': 123}, c.red.values
    assert {'a': 123}, c.green.values

def test_too_many_signals():
    s = signal.Signal()
    for i in range(21):
        s.set(str(i), 1)

    with pytest.raises(TypeError):
        cc.ConstantCombinator(s)
