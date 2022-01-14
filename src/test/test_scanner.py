import assembler

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

def test_pseudo_instructions():
    scan('pseudo_instructions')

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

    assert expected_text == actual_text
