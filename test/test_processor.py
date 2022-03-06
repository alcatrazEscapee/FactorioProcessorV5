from assembler import Assembler
from processor import Processor

import utils
import pytest


def test_branch_backwards(): run('branch_backwards')
def test_branch_forward(): run('branch_forward')
def test_branch_less_than(): run('branch_less_than')
def test_branch_less_than_equal(): run('branch_less_than_equal')
def test_call_return(): run('call_return')
def test_call_return_nested(): run('call_return_nested')
def test_call_return_special_constant(): run('call_return_special_constant')
def test_fibonacci(): run('fibonacci')
def test_gpu_sprite_image_decoder(): run('gpu_sprite_image_decoder')
def test_gpu_composer(): run('gpu_composer')
def test_halt(): run('halt')
def test_operators_arithmetic(): run('operators_arithmetic')
def test_operators_arithmetic_immediate(): run('operators_arithmetic_immediate')
def test_operators_logical(): run('operators_logical')
def test_operators_logical_immediate(): run('operators_logical_immediate')


def run(file: str):
    file = 'assets/processor/%s.s' % file
    text = utils.read_file(file)
    asm = Assembler(file, text, enable_assertions=True)

    assert asm.assemble(), asm.error

    proc = Processor(asm.code, asm.sprites, exception_handle=lambda p, e: pytest.fail(str(e) + '\n\n' + p.debug_view(), False))
    proc.run()
