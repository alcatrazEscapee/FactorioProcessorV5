from simulator.signal import Signal


def test_add():
    s1 = Signal()
    s1.set('a', 3)
    s2 = Signal()
    s2.set('a', 4)
    s2.set('b', 5)
    s3 = s1 + s2
    assert {'a': 7, 'b': 5} == s3.values

def test_clear():
    s1 = Signal()
    s1.set('b', 234)
    assert s1.values
    s1.clear()
    assert not s1.values

def test_update():
    s1 = Signal()
    s1.set('c', 12)
    s2 = Signal()
    s2.update(s1)
    assert s1 != s2
    assert s1.values == s2.values
