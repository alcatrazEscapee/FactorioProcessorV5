from assembler import Assembler
from processor import Processor

import utils
import pytest
import processor


def test_branch_backwards(): run('branch_backwards')
def test_branch_forward(): run('branch_forward')
def test_call_return(): run('call_return')
def test_call_return_nested(): run('call_return_nested')
def test_call_return_special_constant(): run('call_return_special_constant')
def test_fibonacci(): run('fibonacci')
def test_halt(): run('halt')
def test_operators_arithmetic(): run('operators_arithmetic')
def test_operators_arithmetic_immediate(): run('operators_arithmetic_immediate')
def test_operators_logical(): run('operators_logical')


def run(file: str):
    file = 'assets/processor/%s.s' % file
    text = utils.read_file(file)
    asm = Assembler(file, text, enable_assertions=True)

    assert asm.assemble(), asm.error

    proc = Processor(exception_handle=lambda p, e: pytest.fail(str(e) + '\n\n' + processor.debug_view(p), False))
    proc.load(asm.code, asm.sprites)
    proc.run()

    assert proc.error_code == 0
