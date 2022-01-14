import assembler
import testfixtures

TEST_DIR = '../../tests/scanner/'

def test_empty():
    scan('empty')

def test_syntax():
    scan('syntax')

def test_integer_binary_out_of_bounds():
    scan('integer_binary_out_of_bounds')

def test_integer_hex_out_of_bounds():
    scan('integer_hex_out_of_bounds')

def test_integer_invalid_binary():
    scan('integer_invalid_binary')

def test_integer_invalid_hex():
    scan('integer_invalid_hex')

def test_integer_invalid_non_numeric():
    scan('integer_invalid_non_numeric')

def test_integer_invalid_prefix():
    scan('integer_invalid_prefix')

def test_integer_signed_out_of_bounds():
    scan('integer_signed_out_of_bounds')

def test_integers():
    scan('integers')

def test_identifiers():
    scan('identifiers')

def test_instructions():
    scan('instructions')

def test_registers():
    scan('registers')

def test_comments():
    scan('comments')

def test_unknown_token():
    scan('unknown_token')

def scan(file: str):
    scan_text = assembler.read_file(TEST_DIR + file + '.s')
    scanner = assembler.Scanner(scan_text)
    scanner.scan()
    scanner.trace(TEST_DIR + file + '.out')
    actual_text = assembler.read_file(TEST_DIR + file + '.out')
    expected_text = assembler.read_file(TEST_DIR + file + '.trace')

    testfixtures.compare(expected=expected_text, actual=actual_text)
