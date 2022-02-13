from phases import Scanner, Parser

import utils
import testfixtures

TEST_DIR = 'assets/parser/'

def test_address_constant(): parse('address_constant')
def test_address_constant_out_of_range(): parse('address_constant_out_of_range')
def test_address_constant_register(): parse('address_constant_register')
def test_address_indirect(): parse('address_indirect')
def test_address_indirect_offset(): parse('address_indirect_offset')
def test_address_indirect_offset_out_of_range(): parse('address_indirect_offset_out_of_range')
def test_address_indirect_offset_register(): parse('address_indirect_offset_register')
def test_address_indirect_register(): parse('address_indirect_register')
def test_alias(): parse('alias')
def test_alias_address_array_offset(): parse('alias_address_array_offset')
def test_alias_address_constant(): parse('alias_address_constant')
def test_alias_address_indirect(): parse('alias_address_indirect')
def test_alias_address_indirect_offset(): parse('alias_address_indirect_offset')
def test_empty(): parse('empty')
def test_instructions_type_a(): parse('instructions_type_a')
def test_instructions_type_ar(): parse('instructions_type_ar')
def test_instructions_type_b(): parse('instructions_type_b')
def test_instructions_type_c(): parse('instructions_type_c')
def test_instructions_type_d(): parse('instructions_type_d')
def test_instructions_type_dr(): parse('instructions_type_dr')
def test_duplicate_label(): parse('label_duplicate')
def test_label_missing_colon(): parse('label_missing_colon')
def test_label_not_defined_by_end(): parse('label_not_defined_by_end')
def test_labels(): parse('labels')
def test_sprite(): parse('sprite')
def test_sprite_array(): parse('sprite_array')
def test_sprite_reference(): parse('sprite_reference')
def test_sprite_reference_array(): parse('sprite_reference_array')
def test_word(): parse('word')
def test_word_array(): parse('word_array')
def test_word_array_with_comma(): parse('word_array_with_comma')
def test_word_with_comma(): parse('word_with_comma')


def parse(file: str):
    scan_text = utils.read_or_create_empty(TEST_DIR + file + '.s')
    scanner = Scanner(scan_text)

    assert scanner.scan()

    parser = Parser(scanner.output_tokens, root=TEST_DIR)
    parser.parse()
    parser.trace(TEST_DIR + file + '.out', scanner)
    actual_text = utils.read_or_create_empty(TEST_DIR + file + '.out')
    expected_text = utils.read_or_create_empty(TEST_DIR + file + '.trace')

    testfixtures.compare(expected=expected_text, actual=actual_text)
