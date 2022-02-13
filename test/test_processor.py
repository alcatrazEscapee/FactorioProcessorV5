from assembler import Assembler

import utils
import pytest
import processor


TEST_DIR = 'assets/processor/'

def test_arithmetic():
    run('arithmetic')

def test_fibonacci():
    run('fibonacci')

def test_halt():
    run('halt')

def run(file: str):
    text = utils.read_file(TEST_DIR + file + '.s')
    asm = Assembler(text, 'interpreted')

    assert asm.assemble(), asm.error

    proc = processor.Processor(asm.asserts, lambda p: pytest.fail(processor.create_assert_debug_view(p), False))
    proc.load(asm.code)
    proc.run()

    assert proc.error_code == 0
