# This is an Assembler from assembly code to binary level instructions for the ProcessorV5 architecture
# The purpose is to be able to write programs for the final implementation and hardware model levels

from typing import Optional, Tuple, List, Dict, Literal, Any

from phases import Scanner, Parser, CodeGen

import sys
import utils
import argparse
import blueprint
import dissasembler


def read_command_line_args():
    parser = argparse.ArgumentParser(description='Assembler for Factorio ProcessorV5 architecture')

    parser.add_argument('file', type=str, help='The assembly file to be compiled')
    parser.add_argument('-o', action='store_true', dest='output_binary', help='Output a binary file')
    parser.add_argument('-v', action='store_true', dest='output_viewable', help='Output a hybrid view/disassembly file')
    parser.add_argument('-b', action='store_true', dest='output_blueprint', help='Output a blueprint string for a 60KB ROM')
    parser.add_argument('--out', type=str, help='The output file name')
    return parser.parse_args()

def main(args: argparse.Namespace):
    input_text = utils.read_file(args.file)
    asm = Assembler(input_text)
    if not asm.assemble():
        print(asm.error)
        sys.exit(1)

    output_file = args.file if args.out is None else args.out

    if args.output_binary:
        with open(output_file + '.o', 'wb') as f:
            for c in asm.code:
                f.write(c.to_bytes(8, byteorder='big'))

    if args.output_viewable:
        dis = dissasembler.decode(asm.code)
        with open(output_file + '.v', 'w', encoding='utf-8') as f:
            for c, line in zip(asm.code, dis):
                f.write('%s %s | %s\n' % (
                    bin(utils.bitfield_uint64(c, 32, 32))[2:].zfill(32),
                    bin(utils.bitfield_uint64(c, 0, 32))[2:].zfill(32),
                    line
                ))

    if args.output_blueprint:
        data = encode_as_blueprint(asm.code)
        with open(output_file + '.blueprint', 'w', encoding='utf-8') as f:
            f.write(data)


def encode_as_blueprint(code: List[int]):
    with open('./assets/60kb_rom.blueprint') as f:
        data: Any = blueprint.decode_blueprint_string(f.read())

    # Index combinator positions and signals
    entities = data['blueprint']['entities']
    x_positions, y_positions = set(), set()

    for e in entities:
        pos = e['position']
        x_positions.add(pos['x'])
        y_positions.add(pos['y'])

    x_index = {x: i for i, x in enumerate(sorted(x_positions))}
    y_index = {y: i for i, y in enumerate(sorted(y_positions))}

    pos_index = {}
    for e in entities:
        pos = e['position']
        filters = e['control_behavior']['filters']
        signal_index = {}
        for f in filters:
            signal_index[f['index'] - 1] = f
        pos_index[x_index[pos['x']], y_index[pos['y']]] = signal_index

    # Map memory space onto physical space
    for address, word in enumerate(code):
        for port_x, value in enumerate((utils.signed_bitfield_64_to_32(word, 0, 32), utils.signed_bitfield_64_to_32(word, 32, 32))):
            index = address
            index, row_index_y = index // 20, index % 20
            index, row_minor_y = index // 4, index % 4
            index, col_major_x = index // 16, index % 16
            index, row_major_y = index // 6, index % 6

            assert index == 0, 'Address out of bounds for memory size'

            signal = pos_index[(port_x * 16) + col_major_x, (row_major_y * 6) + row_minor_y]
            signal = signal[row_index_y]
            signal['count'] = int(value)

    return blueprint.encode_blueprint_string(data)


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
