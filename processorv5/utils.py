from typing import NamedTuple, Union, Dict, List, Tuple, Callable, Optional, Generator, Any
from multiprocessing.connection import Connection
from threading import Timer
from numpy import int32, uint64
from constants import GPUImageDecoder
from PIL import Image

import os

import constants

AnyInt = Union[int, int32, uint64]
AnyValue = Union[str, AnyInt]

JsonObject = Dict[str, 'Json']
Json = Union[int, str, bool, List['Json'], JsonObject]

def mask_int32(bits: AnyInt) -> int32:
    return (int32(1) << int32(bits)) - int32(1)

def mask_uint64(bits: AnyInt) -> uint64:
    return (uint64(1) << uint64(bits)) - uint64(1)

def bit_int32(x: AnyInt, index: AnyInt) -> int32:
    return (int32(x) >> int32(index)) & int32(1)

def bit_uint64(x: AnyInt, index: AnyInt) -> uint64:
    return (uint64(x) >> uint64(index)) & uint64(1)

def sign_32(x: int32, bits: AnyInt) -> int32:
    sign_bit = bit_int32(x, int32(bits) - int32(1))
    if sign_bit == 1:
        return x - (int32(1) << int32(bits))
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


def read_or_create_empty(file: str) -> str:
    if os.path.isfile(file):
        return read_file(file)
    else:
        with open(file, 'w', encoding='utf-8') as f:
            f.write('\n')
        return ''

def read_file(file: str) -> str:
    with open(file, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file: str, contents: str):
    with open(file, 'w', encoding='utf-8') as f:
        f.write(contents)

def unique_path(file: str) -> str:
    return os.path.normpath(os.path.abspath(file))


class TextureHelper:

    def __init__(self, root: str, err: Callable[[str], None]):
        self.root = root
        self.err = err
        self.textures: Dict[str, str] = {}
        self.cache: Dict[str, Tuple[int, int, Tuple[Tuple[bool, ...], ...]]] = {}

    def load_sprite(self, name: str, x: int, y: int, w: int, h: int) -> str:
        width, height, data = self.load_image(name)
        if x < 0 or y < 0 or x + w > width or y + h > height:
            self.err('Image parameters [%d %d %d %d] are illegal for image \'%s\' with dimensions %d x %d' % (x, y, w, h, name, width, height))
        return '|'.join([''.join(['#' if data[y + dy][x + dx] else '.' for dx in range(w)]) for dy in range(h)])

    def load_image(self, name: str) -> Tuple[int, int, Tuple[Tuple[bool, ...], ...]]:
        if name in self.cache:
            return self.cache[name]
        if name not in self.textures:
            self.err('Referenced unknown texture: \'%s\'' % name)
        name = self.textures[name]
        try:
            im = Image.open(os.path.join(self.root, name))
            im = im.convert('L', dither=Image.NONE)
            width, height = im.width, im.height
            data = tuple(tuple(im.getpixel((ix, iy)) < 127 for ix in range(width)) for iy in range(height))
            self.cache[name] = (width, height, data)
            return width, height, data
        except Exception as e:
            self.err('Unknown error occurred while reading \'%s\': %s' % (name, e))


class ImageBuffer:

    @staticmethod
    def empty() -> 'ImageBuffer':
        return ImageBuffer(())

    @staticmethod
    def unpack(s: str) -> 'ImageBuffer':
        return ImageBuffer(tuple(s.split('|')))

    @staticmethod
    def unpack_decoder(f: GPUImageDecoder, data: int32) -> 'ImageBuffer':
        data = tuple('.#'[bit_int32(data, i)] for i in range(32))
        width = 1 << (5 - f.value)
        height = 1 << f.value
        return ImageBuffer(tuple(tuple(data[x + width * y] for x in range(width)) for y in range(height)))

    @staticmethod
    def create(func: Callable[[int, int], str]) -> 'ImageBuffer':
        return ImageBuffer(tuple(tuple(func(x, y) for x in range(constants.SCREEN_WIDTH)) for y in range(constants.SCREEN_HEIGHT)))

    def __init__(self, data: Tuple[str, ...] | Tuple[Tuple[str, ...], ...]):
        self.data: Tuple[str, ...] | Tuple[Tuple[str, ...], ...] = data

    def __getitem__(self, item: Tuple[int, int]) -> str:
        x, y = item
        if 0 <= y < len(self.data) and 0 <= x < len(row := self.data[y]):
            return row[x]
        return '.'


class ConnectionManager:
    """
    Helper for the base pipe connection API, allows re-opening of new pipes, and enforces a basic send/receive protocol
    """

    def __init__(self, pipe: Optional[Connection] = None):
        self.pipe: Optional[Connection] = pipe

    def closed(self) -> bool:
        return self.pipe is None

    def reopen(self, pipe: Connection):
        self.pipe = pipe

    def send(self, key: str, *data: Any):
        if self.pipe is not None:
            try:
                self.pipe.send((key, *data))
            except BrokenPipeError:
                self.pipe = None

    def poll(self) -> Generator[Tuple[Any, ...], None, None]:
        try:
            while self.pipe is not None and self.pipe.poll():
                yield self.pipe.recv()
        except BrokenPipeError:
            self.pipe = None


class KeyDebouncer:
    """ Debounces key events for Tkinter, so press-and-hold works. Modified from https://github.com/adamheins/tk-debouncer """

    def __init__(self, callback: Callable[[Any, bool], None]):
        self.pressed: bool = False
        self.release_timer: Timer | None = None
        self.callback = callback

    def on_pressed(self, event):
        if self.release_timer:
            self.release_timer.cancel()
            self.release_timer = None
        if not self.pressed:
            self.pressed = True
            self.callback(event, True)

    def on_released(self, event):
        # Set a timer. If it is allowed to expire (not reset by another down event), then we know the key has been released for good.
        self.release_timer = Timer(0.05, self.on_timer_expire, [event])
        self.release_timer.start()

    def on_timer_expire(self, event):
        self.pressed = False
        self.callback(event, False)
