from typing import NamedTuple, Union
from numpy import int32, uint64


AnyInt = Union[int, int32, uint64]
AnyValue = Union[str, AnyInt]


def mask_int32(bits: AnyInt) -> int32:
    return (int32(1) << int32(bits)) - int32(1)

def mask_uint64(bits: AnyInt) -> uint64:
    return (uint64(1) << uint64(bits)) - uint64(1)

def bit_int32(x: AnyInt, index: AnyInt) -> int32:
    return (int32(x) >> int32(index)) & int32(1)

def bit_uint64(x: AnyInt, index: AnyInt) -> uint64:
    return (uint64(x) >> uint64(index)) & uint64(1)

def sign_32(x: int32, bits: int32) -> int32:
    sign_bit = bit_int32(x, bits - int32(1))
    if sign_bit == 1:
        return x - (int32(1) << bits)
    else:
        return x

def sign_64_to_32(x: uint64, bits: uint64) -> int32:
    sign_bit = bit_uint64(x, bits - uint64(1))
    if sign_bit == 1:
        return int32(x) - (int32(1) << int32(bits))
    else:
        return int32(x)

def bitfield_int32(x: AnyInt, offset: AnyInt, bits: AnyInt) -> int32:
    return (int32(x) >> int32(offset)) & mask_int32(bits)

def bitfield_uint64(x: AnyInt, offset: AnyInt, bits: AnyInt) -> uint64:
    return (uint64(x) >> uint64(offset)) & mask_uint64(bits)

def signed_bitfield_64_to_32(value: AnyInt, offset: AnyInt, bits: AnyInt) -> int32:
    return sign_64_to_32(bitfield_uint64(value, offset, bits), bits)

def signed_bitfield_32(value: AnyInt, offset: AnyInt, bits: AnyInt) -> int32:
    return sign_32(bitfield_int32(value, offset, bits), bits)


def to_bitfield(value: int, bits: int, offset: int) -> int:
    interval_bitfield(bits, False).require(value)
    return value << offset

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


def read_file(file: str) -> str:
    with open(file) as f:
        return f.read()
