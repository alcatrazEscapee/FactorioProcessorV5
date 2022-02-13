from phases import Scanner

import utils
import testfixtures


TEST_DIR = 'assets/scanner/'


def test_comments(): scan('comments')
def test_empty(): scan('empty')
def test_identifiers(): scan('identifiers')
def test_instructions(): scan('instructions')
def test_integer_binary_out_of_bounds(): scan('integer_binary_out_of_bounds')
def test_integer_hex_out_of_bounds(): scan('integer_hex_out_of_bounds')
def test_integer_invalid_binary(): scan('integer_invalid_binary')
def test_integer_invalid_hex(): scan('integer_invalid_hex')
def test_integer_invalid_non_numeric(): scan('integer_invalid_non_numeric')
def test_integer_invalid_prefix(): scan('integer_invalid_prefix')
def test_integer_signed_out_of_bounds(): scan('integer_signed_out_of_bounds')
def test_integers(): scan('integers')
def test_keywords(): scan('keywords')
def test_registers(): scan('registers')
def test_sprite_literal(): scan('sprite_literal')
def test_string_literal(): scan('string_literal')
def test_syntax(): scan('syntax')
def test_unknown_token(): scan('unknown_token')

def scan(file: str):
    scan_text = utils.read_or_create_empty(TEST_DIR + file + '.s')
    scanner = Scanner(scan_text)
    scanner.scan()
    scanner.trace(TEST_DIR + file + '.out')
    actual_text = utils.read_or_create_empty(TEST_DIR + file + '.out')
    expected_text = utils.read_or_create_empty(TEST_DIR + file + '.trace')

    testfixtures.compare(expected=expected_text, actual=actual_text)
