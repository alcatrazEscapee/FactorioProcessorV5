from phases import Scanner, Parser, CodeGen

import utils
import dissasembler
import testfixtures

TEST_DIR = 'assets/codegen/'


def test_empty(): gen('empty')
def test_instructions_type_a(): gen('instructions_type_a')
def test_instructions_type_ar(): gen('instructions_type_ar')
def test_instructions_type_b(): gen('instructions_type_b')
def test_instructions_type_c(): gen('instructions_type_c')
def test_instructions_type_d(): gen('instructions_type_d')
def test_instructions_type_dr(): gen('instructions_type_dr')
def test_instructions_type_f(): gen('instructions_type_f')


def gen(file: str):
    scan_text = utils.read_or_create_empty(TEST_DIR + file + '.s')
    scanner = Scanner(scan_text)

    assert scanner.scan()

    parser = Parser(scanner.output_tokens)

    assert parser.parse()

    codegen = CodeGen(parser)
    codegen.gen()
    actual_text = '\n'.join(dissasembler.decode(codegen.output_code)) + '\n'
    utils.write_file(TEST_DIR + file + '.out', actual_text)
    expected_text = utils.read_or_create_empty(TEST_DIR + file + '.trace')

    testfixtures.compare(actual=actual_text, expected=expected_text)
