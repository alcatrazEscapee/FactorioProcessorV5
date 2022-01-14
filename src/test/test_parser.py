import assembler
import testfixtures

TEST_DIR = '../../tests/parser/'

def test_address_constant():
    parse('address_constant')

def test_address_constant_out_of_range():
    parse('address_constant_out_of_range')

def test_address_constant_register():
    parse('address_constant_register')

def test_address_indirect():
    parse('address_indirect')

def test_address_indirect_offset():
    parse('address_indirect_offset')

def test_address_indirect_offset_out_of_range():
    parse('address_indirect_offset_out_of_range')

def test_address_indirect_offset_register():
    parse('address_indirect_offset_register')

def test_address_indirect_register():
    parse('address_indirect_register')

def test_alias():
    parse('alias')

def test_alias_address_constant():
    parse('alias_address_constant')

def test_alias_address_indirect():
    parse('alias_address_indirect')

def test_alias_address_indirect_offset():
    parse('alias_address_indirect_offset')

def test_empty():
    parse('empty')

def test_instructions_type_a():
    parse('instructions_type_a')

def test_instructions_type_ar():
    parse('instructions_type_ar')

def test_instructions_type_b():
    parse('instructions_type_b')

def test_duplicate_label():
    parse('label_duplicate')

def test_label_missing_colon():
    parse('label_missing_colon')

def test_labels():
    parse('labels')


def parse(file: str):
    scan_text = assembler.read_file(TEST_DIR + file + '.s')
    expected_text = assembler.read_file(TEST_DIR + file + '.trace')
    scanner = assembler.Scanner(scan_text)

    assert scanner.scan()

    parser = assembler.Parser(scanner.output_tokens)
    parser.parse()
    parser.trace(TEST_DIR + file + '.out', scanner)
    actual_text = assembler.read_file(TEST_DIR + file + '.out')

    testfixtures.compare(expected=expected_text, actual=actual_text)
