# This is an Assembler from assembly code to binary level instructions for the ProcessorV5 architecture
# The purpose is to be able to write programs for the final implementation and hardware model levels

from typing import Optional, Tuple, List, Dict, Literal

from phases import Scanner, Parser, CodeGen

import sys
import utils
import argparse
import dissasembler


def read_command_line_args():
    parser = argparse.ArgumentParser(description='Assembler for Factorio ProcessorV5 architecture')

    parser.add_argument('file', type=str, help='The assembly file to be compiled')
    parser.add_argument('-o', action='store_true', dest='output_binary', help='Output a binary file')
    parser.add_argument('-v', action='store_true', dest='output_viewable', help='Output a hybrid view/disassembly file')
    return parser.parse_args()

def main(args: argparse.Namespace):
    input_text = utils.read_file(args.file)
    asm = Assembler(input_text)
    if not asm.assemble():
        print(asm.error)
        sys.exit(1)

    if args.output_binary:
        with open(args.file + '.o', 'wb') as f:
            for c in asm.code:
                f.write(c.to_bytes(8, byteorder='big'))

    if args.output_viewable:
        dis = dissasembler.decode(asm.code)
        with open(args.file + '.v', 'w', encoding='utf-8') as f:
            for c, line in zip(asm.code, dis):
                f.write('%-12d %-12d | %s\n' % (utils.signed_bitfield_64_to_32(c, 32, 32), utils.signed_bitfield_64_to_32(c, 0, 32), line))


class Assembler:

    def __init__(self, input_text: str, assert_mode: Literal['native', 'interpreted', 'none'] = 'none'):
        self.input_text = input_text
        self.assert_mode = assert_mode

        self.code: Optional[List[int]] = None
        self.asserts: Optional[Dict[int, Tuple[int, int]]] = None
        self.error: Optional[str] = None

    def assemble(self) -> bool:
        scanner = Scanner(self.input_text)
        if not scanner.scan():
            self.error = 'Scanner error:\n%s' % scanner.error
            return False

        parser = Parser(scanner.output_tokens, self.assert_mode)
        if not parser.parse():
            parser.error.trace(scanner)
            self.error = 'Parser error:\n%s' % parser.error
            return False

        codegen = CodeGen(parser.output_tokens, parser.labels)
        codegen.gen()

        self.code = codegen.output_code
        self.asserts = codegen.asserts
        return True


if __name__ == '__main__':
    main(read_command_line_args())
