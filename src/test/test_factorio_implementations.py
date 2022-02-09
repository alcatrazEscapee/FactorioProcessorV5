from simulator import Simulator, ConstantCombinator, ArithmeticCombinator
from numpy import int32

import utils
import random

BLUEPRINT_DIR = '../../tests/blueprints/'


def test_edge_detector():
    load('edge_detector')

def test_rising_edge_detector():
    model = load('rising_edge_detector')

def test_twos_compliment_decoder():
    model = load('twos_compliment_decoder')

    a_in = model.find('a in', ConstantCombinator)
    a_out = model.find('a out', ConstantCombinator)
    a_mask = model.find('s:=a&4', ArithmeticCombinator)
    a_max = model.find('a:=a-8', ArithmeticCombinator)

    for _ in range(1000):
        bits = randint(2, 30)

        setup_unsigned = randint32(0, 1 << bits)
        setup_signed = utils.sign_32(setup_unsigned, bits)

        target_unsigned = randint32(0, 1 << bits)
        target_signed = utils.sign_32(target_unsigned, bits)

        # Setup
        a_in.set('a', setup_unsigned)
        a_mask.set_right(1 << (bits - 1))
        a_max.set_right(1 << bits)
        model.tick_until_stable()

        assert a_out.get('a') == setup_signed, 'Bits: %d, U: %d, S: %d' % (bits, setup_unsigned, setup_signed)

        # Timing
        a_in.set('a', target_unsigned)
        assert model.tick_until_stable() <= 2, 'Bits: %d, U: %d, S: %d -> U: %d, S: %d' % (bits, setup_unsigned, setup_signed, target_unsigned, target_signed)

        # Validation
        assert a_out.get('a') == target_signed, 'Bits: %d, U: %d, S: %d' % (bits, target_unsigned, target_signed)


def test_twos_compliment_encoder():
    model = load('twos_compliment_encoder')

    a_in = model.find('a in', ConstantCombinator)
    a_out = model.find('a out', ConstantCombinator)
    a_const = model.find('a max', ConstantCombinator)

    for _ in range(1000):
        bits = randint(2, 30)

        setup_unsigned = randint32(0, 1 << bits)
        setup_signed = utils.sign_32(setup_unsigned, bits)

        target_unsigned = randint32(0, 1 << bits)
        target_signed = utils.sign_32(target_unsigned, bits)

        # Setup
        a_const.set('a', 1 << bits)
        a_in.set('a', setup_signed)
        model.tick_until_stable()

        assert a_out.get('a') == setup_unsigned, 'Bits: %d, U: %d, S: %d' % (bits, setup_unsigned, setup_signed)

        # Timing
        a_in.set('a', target_signed)
        assert model.tick_until_stable() <= 2, 'Bits: %d, U: %d, S: %d -> U: %d, S: %d' % (bits, setup_unsigned, setup_signed, target_unsigned, target_signed)

        # Validation
        assert a_out.get('a') == target_unsigned, 'Bits: %d, U: %d, S: %d' % (bits, target_unsigned, target_signed)

def randint(a: int, b: int) -> int:
    return random.randint(a, b)

def randint32(a: int = -(1 << 31), b: int = (1 << 31) - 1) -> int32:
    return int32(random.randint(a, b))

def load(file: str) -> Simulator:
    return Simulator(utils.read_file(BLUEPRINT_DIR + file + '.txt'))
