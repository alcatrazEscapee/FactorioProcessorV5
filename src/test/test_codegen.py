from phases import Scanner, Parser, CodeGen

import utils
import dissasembler
import testfixtures

TEST_DIR = '../../tests/codegen/'


def test_arithmetic1():
    gen('arithmetic1')

def test_empty():
    gen('empty')

def gen(file: str):
    scan_text = utils.read_file(TEST_DIR + file + '.s')
    scanner = Scanner(scan_text)

    assert scanner.scan()

    parser = Parser(scanner.output_tokens)

    assert parser.parse()

    codegen = CodeGen(parser.output_tokens, parser.labels)
    codegen.gen()
    actual_text = '\n'.join(dissasembler.decode(codegen.output_code))
    expected_text = utils.read_file(TEST_DIR + file + '.trace')

    testfixtures.compare(actual=actual_text, expected=expected_text)
