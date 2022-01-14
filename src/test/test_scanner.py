import assembler
import testfixtures

TEST_DIR = '../../tests/scanner/'

def test_empty():
    scan('empty')

def test_syntax():
    scan('syntax')

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
    expected_text = assembler.read_file(TEST_DIR + file + '.trace')
    scanner = assembler.Scanner(scan_text)
    scanner.scan()
    scanner.trace(TEST_DIR + file + '.out')
    actual_text = assembler.read_file(TEST_DIR + file + '.out')

    testfixtures.compare(expected=expected_text, actual=actual_text)
