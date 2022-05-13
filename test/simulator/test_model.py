from typing import Callable, Any
from simulator import ModelBuilder, ArithmeticCombinator, DeciderCombinator, ArithmeticOperation, DeciderOperation


def run(builder: Callable[[ModelBuilder], None], expected: Any):
    b = ModelBuilder()
    builder(b)
    assert len(b.model.entities) == 1
    assert expected == b.model.entities[0]


def test_ac_1(): run(lambda b: b.ac('x := y + z'), ArithmeticCombinator('y', 'z', 'x', ArithmeticOperation.ADD))
def test_ac_2(): run(lambda b: b.ac('x := y - 3'), ArithmeticCombinator('y', 3, 'x', ArithmeticOperation.SUBTRACT))
def test_ac_3(): run(lambda b: b.ac('x0:= y0*z0'), ArithmeticCombinator('y0', 'z0', 'x0', ArithmeticOperation.MULTIPLY))
def test_ac_4(): run(lambda b: b.ac('each := each * 3'), ArithmeticCombinator('each', 3, 'each', ArithmeticOperation.MULTIPLY))
def test_ac_5(): run(lambda b: b.ac('a := each % 2'), ArithmeticCombinator('each', 2, 'a', ArithmeticOperation.MODULO))

def test_dc_1(): run(lambda b: b.dc('x=1 if a>b'), DeciderCombinator('a', 'b', 'x', DeciderOperation.GREATER_THAN, False))
def test_dc_2(): run(lambda b: b.dc('x if a>b'), DeciderCombinator('a', 'b', 'x', DeciderOperation.GREATER_THAN, True))
def test_dc_3(): run(lambda b: b.dc('everything=1 if x=y'), DeciderCombinator('x', 'y', 'everything', DeciderOperation.EQUAL, False))
def test_dc_4(): run(lambda b: b.dc('everything if x=y'), DeciderCombinator('x', 'y', 'everything', DeciderOperation.EQUAL, True))
def test_dc_5(): run(lambda b: b.dc('each=1 if each<5'), DeciderCombinator('each', 5, 'each', DeciderOperation.LESS_THAN, False))
def test_dc_6(): run(lambda b: b.dc('each if each<5'), DeciderCombinator('each', 5, 'each', DeciderOperation.LESS_THAN, True))

