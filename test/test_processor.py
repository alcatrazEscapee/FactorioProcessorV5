from assembler import Assembler

import utils
import pytest
import processor
import dissasembler


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

    proc = processor.Processor(asm.asserts, handler)
    proc.load(asm.code)
    proc.run()

    assert proc.error_code == 0

def handler(proc: processor.Processor):
    # Synthetic / Interpreted assertion handler
    addr, expected = proc.asserts[proc.pc]
    actual = proc.mem_get_operand(addr)
    reg = dissasembler.decode_address(addr)

    # Show an area around the non-zero memory
    memory_view = set()
    for i, m in enumerate(proc.memory):
        if m != 0:
            memory_view |= {i - 1, i, i + 1}

    # Show a view of the assembly near the area
    decoded = dissasembler.decode(proc.instructions)
    decoded_view = decoded[proc.pc - 3:proc.pc] + [decoded[proc.pc] + ' <-- HERE'] + decoded[proc.pc + 1:proc.pc + 4]

    pytest.fail('\n'.join([
        'At: assert %s = %d (got %d)' % (reg, expected, actual),
        'PC: %d' % proc.pc,
        '',
        'Disassembly:',
        *decoded_view,
        '',
        'Memory:',
        'Addr | Hex  | Dec',
        *['%04d | %s | %d' % (i, format(m, '04x'), m) for i, m in enumerate(proc.memory) if i in memory_view]
    ]), False)
