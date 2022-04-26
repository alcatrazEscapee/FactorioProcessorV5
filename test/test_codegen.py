from phases import Scanner, Parser, CodeGen

import utils
import disassembler
import testfixtures


def test_empty(): gen('empty')
def test_instructions_type_a(): gen('instructions_type_a')
def test_instructions_type_ar(): gen('instructions_type_ar')
def test_instructions_type_b(): gen('instructions_type_b')
def test_instructions_type_c(): gen('instructions_type_c')
def test_instructions_type_d(): gen('instructions_type_d')
def test_instructions_type_dr(): gen('instructions_type_dr')
def test_instructions_type_f(): gen('instructions_type_f')


def gen(file: str):
    file = 'assets/codegen/%s.s' % file
    scan_text = utils.read_or_create_empty(file)
    scanner = Scanner(scan_text)

    assert scanner.scan()

    parser = Parser(scanner.output_tokens, file=file)

    assert parser.parse()

    codegen = CodeGen(parser)
    codegen.gen()
    actual_text = '\n'.join(disassembler.decode(codegen.output_code, label_table=parser.label_table())) + '\n'
    utils.write_file(file.replace('.s', '.out'), actual_text)
    expected_text = utils.read_or_create_empty(file.replace('.s', '.trace'))

    testfixtures.compare(actual=actual_text, expected=expected_text)
