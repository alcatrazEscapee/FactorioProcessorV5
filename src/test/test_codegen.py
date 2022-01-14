import assembler

TEST_DIR = '../../tests/codegen/'


def test_arithmetic1():
    gen('arithmetic1')

def test_empty():
    gen('empty')


def gen(file: str):
    scan_text = assembler.read_file(TEST_DIR + file + '.s')
    scanner = assembler.Scanner(scan_text)

    assert scanner.scan()

    parser = assembler.Parser(scanner.output_tokens)

    assert parser.parse()

    codegen = assembler.CodeGen(parser.output_tokens)

    codegen.gen()
    codegen.trace(TEST_DIR + file + '.out')
    actual_text = assembler.read_file(TEST_DIR + file + '.out')
    expected_text = assembler.read_file(TEST_DIR + file + '.trace')

    assert expected_text == actual_text
