# This is an Assembler from assembly code to binary level instructions for the ProcessorV5 architecture
# The purpose is to be able to write programs for the final implementation and hardware model levels

from typing import Optional, Tuple, List, Dict

from phases import Scanner, Parser, CodeGen
from constants import Registers

import sys
import utils
import builder
import argparse
import disassembler


def read_command_line_args():
    parser = argparse.ArgumentParser(description='Assembler for Factorio ProcessorV5 architecture')

    parser.add_argument('file', type=str, help='The assembly file to be compiled')

    parser.add_argument('--object', action='store_true', dest='output_binary', help='Output a binary file')
    parser.add_argument('--disassembly', action='store_true', dest='output_viewable', help='Output a hybrid view/disassembly file')
    parser.add_argument('--factorio-blueprint', action='store_true', dest='output_blueprint', help='Output a blueprint string')
    parser.add_argument('--factorio-memory-map', action='store_true', dest='output_factorio_memory_map', help='Output a Factorio Memory Mapping file to <file>.fmap')

    parser.add_argument('--ea', action='store_true', dest='enable_assertions', default=False, help='Enable assert instructions in the output code')
    parser.add_argument('--ep', action='store_true', dest='enable_print', default=False, help='Enable print instructions in the output code')
    parser.add_argument('--out', type=str, help='The output file name')

    return parser.parse_args()

def main(args: argparse.Namespace):
    input_text = utils.read_file(args.file)
    asm = Assembler(args.file, input_text, args.enable_assertions, args.enable_print)
    if not asm.assemble():
        print(asm.error)
        sys.exit(1)

    output_file = args.file if args.out is None else args.out

    if args.output_binary:
        with open(output_file + '.o', 'wb') as f:
            for c in asm.code:
                f.write(c.to_bytes(8, byteorder='big'))

    if args.output_viewable:
        dis = disassembler.decode(asm.code, asm.print_table, asm.memory_table, asm.label_table)
        with open(output_file + '.v', 'w', encoding='utf-8') as f:
            for c, line in zip(asm.code, dis):
                f.write('%s %s | %s\n' % (
                    bin(utils.bitfield_uint64(c, 32, 32))[2:].zfill(32),
                    bin(utils.bitfield_uint64(c, 0, 32))[2:].zfill(32),
                    line
                ))

    if args.output_blueprint:
        data = builder.build_rom(asm.code, asm.sprites)
        with open(output_file + '.blueprint', 'w', encoding='utf-8') as f:
            f.write(data)

    if args.output_factorio_memory_map:
        with open(output_file + '.fmap', 'w', encoding='utf-8') as f:
            format_string = '%04d | %-' + str(1 + max(len(s) for s in asm.memory_table.values())) + 's | %d, %s\n'
            for r in Registers:
                f.write(format_string % (r.value, r.name, r.value // 32, builder.SIGNALS_32BIT[r.value % 32]))
            for address, name in sorted(asm.memory_table.items()):
                f.write(format_string % (address, name, address // 32, builder.SIGNALS_32BIT[address % 32]))


class Assembler:

    def __init__(self, file_name: str, input_text: str, enable_assertions: bool = False, enable_print: bool = False):
        self.file_name = file_name
        self.input_text = input_text
        self.enable_assertions = enable_assertions
        self.enable_print = enable_print

        self.code: List[int] = []
        self.sprites: List[str] = []
        self.directives: Dict[str, str] = {}
        self.print_table: List[Tuple[str, Tuple[int, ...]]] = []
        self.memory_table: Dict[int, str] = {}
        self.label_table: Dict[int, str] = {}
        self.error: Optional[str] = None

    def assemble(self) -> bool:
        scanner = Scanner(self.input_text)
        if not scanner.scan():
            self.error = 'Scanner error:\n%s' % scanner.error
            return False

        parser = Parser(scanner.output_tokens, self.file_name, self.enable_assertions, self.enable_print)
        if not parser.parse():
            parser.error.trace(scanner)
            self.error = 'Parser error:\n%s' % parser.error
            return False

        codegen = CodeGen(parser)
        codegen.gen()

        self.code = codegen.output_code
        self.sprites = codegen.sprites
        self.directives = scanner.directives
        self.print_table = codegen.print_table
        self.memory_table = parser.memory_table
        self.label_table = parser.label_table()
        return True


if __name__ == '__main__':
    main(read_command_line_args())
