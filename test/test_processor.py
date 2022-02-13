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

    proc = processor.Processor(asm.asserts, exception_handle=lambda p, e: pytest.fail(str(e) + '\n\n' + processor.debug_view(p), False))
    proc.load(asm.code)
    proc.run()

    assert proc.error_code == 0
