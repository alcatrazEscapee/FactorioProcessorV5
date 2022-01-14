import utils
import pytest

from utils import Interval


def test_sign():
    assert utils.sign(0b000, 3) == 0
    assert utils.sign(0b001, 3) == 1
    assert utils.sign(0b010, 3) == 2
    assert utils.sign(0b011, 3) == 3
    assert utils.sign(0b100, 3) == -4
    assert utils.sign(0b101, 3) == -3
    assert utils.sign(0b110, 3) == -2
    assert utils.sign(0b111, 3) == -1

def test_sign_out_of_bounds():
    with pytest.raises(AssertionError):
        utils.sign(0b1000, 3)

def test_invert():
    assert utils.invert(0b11111111, 3) == 0b11111000
    assert utils.invert(0b1100110101011010, 5) == 0b1100110101000101

def test_mask():
    assert utils.mask(1) == 0b1
    assert utils.mask(6) == 0b111111

def test_mask_out_of_bounds():
    with pytest.raises(AssertionError):
        utils.mask(0)

def test_bit():
    value = 0b1101010011010101
    bits = [1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1]

    for i, b in enumerate(bits[::-1]):
        assert utils.bit(value, i) == b, 'Index: %d' % i

def test_bitfield_to_bitfield_inverse():
    for bits in range(2, 7):
        for value in range(0, 1 << bits):
            for offset in range(0, 8):
                b = utils.to_bitfield(value, bits, offset)
                assert utils.bitfield(b, offset, bits) == value, 'bits: %d, value: %s, offset: %d, bitfield: %s' % (bits, bin(value), offset, bin(b))

def test_signed_bitfield_to_signed_bitfield_inverse():
    for bits in range(2, 7):
        for value in range(-(1 << (bits - 1)), 1 << (bits - 1)):
            for offset in range(0, 8):
                b = utils.to_signed_bitfield(value, bits, offset)
                assert utils.signed_bitfield(b, offset, bits) == value, 'bits: %d, value: %s, offset: %d, bitfield: %s' % (bits, bin(value), offset, bin(b))

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
