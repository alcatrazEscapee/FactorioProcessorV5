from typing import NamedTuple


def sign(x: int, bits: int) -> int:
    """ Converts a N-bit 2's compliment value to a signed integer """
    assert x == bitfield(x, 0, bits)
    sign_bit = bit(x, bits - 1)
    if sign_bit == 1:
        return x - (1 << bits)
    else:
        return x


def invert(x: int, bits: int) -> int:
    """ Inverts the first N bits of x """
    assert bits > 0
    return x ^ mask(bits)


def mask(bits: int) -> int:
    """ Returns the value 0b11...1 with N ones """
    assert bits > 0
    return (1 << bits) - 1


def bit(x: int, index: int) -> int:
    """ Returns the Nth bit of x """
    return (x >> index) & 1


def bitfield(x: int, offset: int, bits: int) -> int:
    """ Returns the bits-length bit field of x, with an offset of index from the LSB """
    return (x >> offset) & mask(bits)


def to_bitfield(value: int, bits: int, offset: int) -> int:
    interval_bitfield(bits, False).require(value)
    return value << offset


def signed_bitfield(value: int, index: int, bits: int) -> int:
    """ Returns the bits-length bit field of x, with an offset of index from the LSB, decoded into a signed integer from a two's compliment representation """
    return sign(bitfield(value, index, bits), bits)


def to_signed_bitfield(value: int, bits: int, offset: int) -> int:
    interval_bitfield(bits, True).require(value)
    if value < 0:
        return (value + (1 << bits)) << offset
    else:
        return value << offset


class Interval(NamedTuple):
    min: int
    max: int
    error_template: str

    def check(self, value: int) -> bool:
        return self.min <= value <= self.max

    def error(self, value: int) -> str:
        return self.error_template % value

    def require(self, value: int):
        assert self.check(value), self.error(value)

def interval_range(min_inclusive: int, max_inclusive: int) -> Interval:
    return Interval(min_inclusive, max_inclusive, 'Value %s outside of range [%d, %d]' % ('%d', min_inclusive, max_inclusive))

def interval_bitfield(bits: int, signed: bool) -> Interval:
    if signed:
        bound = 1 << (bits - 1)
        return Interval(-bound, bound - 1, 'Value %s outside of range [%d, %d] for %d-bit signed field' % ('%d', -bound, bound - 1, bits))
    else:
        bound = 1 << bits
        return Interval(0, bound - 1, 'Value %s outside of range [0, %d] for %d-bit unsigned field' % ('%d', bound - 1, bits))