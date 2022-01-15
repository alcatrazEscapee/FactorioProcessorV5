import utils

from utils import Interval


def test_interval():
    i = Interval(4, 7, 'Invalid %d')
    assert not i.check(3)
    assert i.check(4)
    assert i.check(5)
    assert i.check(7)
    assert not i.check(8)

def test_interval_error():
    i = Interval(0, 4, 'Invalid %d')
    assert i.error(6) == 'Invalid 6'

def test_interval_range():
    i = utils.interval_range(0, 3)
    assert i.min == 0
    assert i.max == 3

def test_interval_signed_bitfield():
    i = utils.interval_bitfield(4, True)
    assert i.min == -8
    assert i.max == 7
    assert i.error_template == 'Value %d outside of range [-8, 7] for 4-bit signed field'

def test_interval_unsigned_bitfield():
    i = utils.interval_bitfield(4, False)
    assert i.min == 0
    assert i.max == 15
    assert i.error_template == 'Value %d outside of range [0, 15] for 4-bit unsigned field'
