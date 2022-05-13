from typing import List, Dict, Tuple, Any, Union, Callable
from constants import Opcodes, GPUInstruction, GPUBufferCode, GPUInputCode, ALUCode, ALUInputCode, PCInputCode, BranchCode
from numpy import int32
from utils import ImageBuffer
from enum import IntEnum

import os
import json
import utils
import blueprint

IntLike = Union[IntEnum, int]

SIGNALS_32BIT = ['wooden-chest', 'iron-chest', 'steel-chest', 'storage-tank', 'transport-belt', 'fast-transport-belt', 'express-transport-belt', 'underground-belt', 'fast-underground-belt', 'express-underground-belt', 'splitter', 'fast-splitter', 'express-splitter', 'burner-inserter', 'inserter', 'long-handed-inserter', 'fast-inserter', 'filter-inserter', 'stack-inserter', 'stack-filter-inserter', 'small-electric-pole', 'medium-electric-pole', 'big-electric-pole', 'substation', 'pipe', 'pipe-to-ground', 'pump', 'rail', 'train-stop', 'rail-signal', 'rail-chain-signal', 'locomotive']
SIGNALS_80 = ['wooden-chest', 'iron-chest', 'steel-chest', 'storage-tank', 'transport-belt', 'fast-transport-belt', 'express-transport-belt', 'underground-belt', 'fast-underground-belt', 'express-underground-belt', 'splitter', 'fast-splitter', 'express-splitter', 'burner-inserter', 'inserter', 'long-handed-inserter', 'fast-inserter', 'filter-inserter', 'stack-inserter', 'stack-filter-inserter', 'small-electric-pole', 'medium-electric-pole', 'big-electric-pole', 'substation', 'pipe', 'pipe-to-ground', 'pump', 'rail', 'train-stop', 'rail-signal', 'rail-chain-signal', 'locomotive', 'cargo-wagon', 'fluid-wagon', 'artillery-wagon', 'car', 'tank', 'spidertron', 'spidertron-remote', 'logistic-robot', 'construction-robot', 'logistic-chest-active-provider', 'logistic-chest-passive-provider', 'logistic-chest-storage', 'logistic-chest-buffer', 'logistic-chest-requester', 'roboport', 'small-lamp', 'red-wire', 'green-wire', 'arithmetic-combinator', 'decider-combinator', 'constant-combinator', 'power-switch', 'programmable-speaker', 'stone-brick', 'concrete', 'hazard-concrete', 'refined-concrete', 'refined-hazard-concrete', 'landfill', 'cliff-explosives', 'repair-pack', 'blueprint', 'deconstruction-planner', 'upgrade-planner', 'blueprint-book', 'boiler', 'steam-engine', 'solar-panel', 'accumulator', 'nuclear-reactor', 'heat-pipe', 'heat-exchanger', 'steam-turbine', 'burner-mining-drill', 'electric-mining-drill', 'offshore-pump', 'pumpjack', 'stone-furnace']

TWO_OPERAND = {'W': 1, 'X': ALUInputCode.A, 'Y': ALUInputCode.B}
OPERAND_IMMEDIATE = {'W': 1, 'X': ALUInputCode.B, 'Y': ALUInputCode.IMMEDIATE}
OPERAND_IMMEDIATE_REVERSE = {'W': 1, 'X': ALUInputCode.IMMEDIATE, 'Y': ALUInputCode.B}
TWO_OPERAND_OFFSET = {'X': ALUInputCode.A, 'Y': ALUInputCode.B, 'S': PCInputCode.OFFSET, 'J': BranchCode.CONDITIONAL}
OPERAND_IMMEDIATE_OFFSET = {'X': ALUInputCode.B, 'Y': ALUInputCode.IMMEDIATE, 'S': PCInputCode.OFFSET, 'J': BranchCode.CONDITIONAL}

INSTRUCTIONS: Dict[Opcodes, Dict[str, IntLike]] = {
    Opcodes.ADD: {**TWO_OPERAND, 'L': ALUCode.ADD},
    Opcodes.SUB: {**TWO_OPERAND, 'L': ALUCode.SUB},
    Opcodes.MUL: {**TWO_OPERAND, 'L': ALUCode.MUL},
    Opcodes.DIV: {**TWO_OPERAND, 'L': ALUCode.DIV},
    Opcodes.POW: {**TWO_OPERAND, 'L': ALUCode.POW},
    Opcodes.MOD: {**TWO_OPERAND, 'L': ALUCode.MOD},
    Opcodes.AND: {**TWO_OPERAND, 'L': ALUCode.AND},
    Opcodes.OR: {**TWO_OPERAND, 'L': ALUCode.OR},
    Opcodes.NAND: {**TWO_OPERAND, 'L': ALUCode.NAND},
    Opcodes.NOR: {**TWO_OPERAND, 'L': ALUCode.NOR},
    Opcodes.XOR: {**TWO_OPERAND, 'L': ALUCode.XOR},
    Opcodes.XNOR: {**TWO_OPERAND, 'L': ALUCode.XNOR},
    Opcodes.LS: {**TWO_OPERAND, 'L': ALUCode.LS},
    Opcodes.RS: {**TWO_OPERAND, 'L': ALUCode.RS},
    Opcodes.EQ: {**TWO_OPERAND, 'L': ALUCode.EQ},
    Opcodes.NE: {**TWO_OPERAND, 'L': ALUCode.NE},
    Opcodes.LT: {**TWO_OPERAND, 'L': ALUCode.LT},
    Opcodes.LE: {**TWO_OPERAND, 'L': ALUCode.LE},
    # Type B
    Opcodes.ADDI: {**OPERAND_IMMEDIATE, 'L': ALUCode.ADD},
    Opcodes.SUBIR: {**OPERAND_IMMEDIATE_REVERSE, 'L': ALUCode.SUB},
    Opcodes.MULI: {**OPERAND_IMMEDIATE, 'L': ALUCode.MUL},
    Opcodes.DIVI: {**OPERAND_IMMEDIATE, 'L': ALUCode.DIV},
    Opcodes.DIVIR: {**OPERAND_IMMEDIATE_REVERSE, 'L': ALUCode.DIV},
    Opcodes.POWI: {**OPERAND_IMMEDIATE, 'L': ALUCode.POW},
    Opcodes.POWIR: {**OPERAND_IMMEDIATE_REVERSE, 'L': ALUCode.POW},
    Opcodes.MODI: {**OPERAND_IMMEDIATE, 'L': ALUCode.MOD},
    Opcodes.MODIR: {**OPERAND_IMMEDIATE_REVERSE, 'L': ALUCode.MOD},
    Opcodes.ANDI: {**OPERAND_IMMEDIATE, 'L': ALUCode.AND},
    Opcodes.ORI: {**OPERAND_IMMEDIATE, 'L': ALUCode.OR},
    Opcodes.NANDI: {**OPERAND_IMMEDIATE, 'L': ALUCode.NAND},
    Opcodes.NORI: {**OPERAND_IMMEDIATE, 'L': ALUCode.NOR},
    Opcodes.XORI: {**OPERAND_IMMEDIATE, 'L': ALUCode.XOR},
    Opcodes.XNORI: {**OPERAND_IMMEDIATE, 'L': ALUCode.XNOR},
    Opcodes.LSI: {**OPERAND_IMMEDIATE, 'L': ALUCode.LS},
    Opcodes.LSIR: {**OPERAND_IMMEDIATE_REVERSE, 'L': ALUCode.LS},
    Opcodes.RSI: {**OPERAND_IMMEDIATE, 'L': ALUCode.RS},
    Opcodes.RSIR: {**OPERAND_IMMEDIATE_REVERSE, 'L': ALUCode.RS},
    Opcodes.EQI: {**OPERAND_IMMEDIATE, 'L': ALUCode.EQ},
    Opcodes.NEI: {**OPERAND_IMMEDIATE, 'L': ALUCode.NE},
    Opcodes.LTI: {**OPERAND_IMMEDIATE, 'L': ALUCode.LT},
    Opcodes.GTI: {**OPERAND_IMMEDIATE, 'L': ALUCode.GT},
    # Type C
    Opcodes.BEQ: {**TWO_OPERAND_OFFSET, 'L': ALUCode.EQ},
    Opcodes.BNE: {**TWO_OPERAND_OFFSET, 'L': ALUCode.NE},
    Opcodes.BLT: {**TWO_OPERAND_OFFSET, 'L': ALUCode.LT},
    Opcodes.BLE: {**TWO_OPERAND_OFFSET, 'L': ALUCode.LE},
    # Type D
    Opcodes.BEQI: {**OPERAND_IMMEDIATE_OFFSET, 'L': ALUCode.EQ},
    Opcodes.BNEI: {**OPERAND_IMMEDIATE_OFFSET, 'L': ALUCode.NE},
    Opcodes.BLTI: {**OPERAND_IMMEDIATE_OFFSET, 'L': ALUCode.LT},
    Opcodes.BGTI: {**OPERAND_IMMEDIATE_OFFSET, 'L': ALUCode.GT},
    # Special (Type E)
    Opcodes.CALL: {'S': PCInputCode.OFFSET, 'J': BranchCode.UNCONDITIONAL, 'R': 1, 'W': 1},
    Opcodes.RET: {'S': PCInputCode.RA, 'A': 0b1111111110_0_00000},
    Opcodes.HALT: {'H': 1},
    Opcodes.ASSERT: {'T': 1},
    Opcodes.GPU: {'G': 1}
}

GPU_INSTRUCTIONS: Dict[GPUInstruction, Dict[str, IntLike]] = {
    GPUInstruction.GFLUSH: {'S': 1},
    GPUInstruction.GLSI: {'I': 1, 'J': GPUBufferCode.GPU_ROM_OUT, 'X': GPUInputCode.IMMEDIATE},
    GPUInstruction.GLS: {'I': 1, 'J': GPUBufferCode.GPU_ROM_OUT, 'X': GPUInputCode.MEMORY},
    GPUInstruction.GLSD: {'I': 1, 'J': GPUBufferCode.IMAGE_DECODER_OUT, 'X': GPUInputCode.MEMORY},
    GPUInstruction.GCB: {'U': 1},
    GPUInstruction.GCI: {'I': 1, 'J': GPUBufferCode.COMPOSER_OUT},
    GPUInstruction.GMV: {'I': 1, 'J': GPUBufferCode.TRANSLATION_MATRIX_OUT, 'X': GPUInputCode.MEMORY, 'Y': GPUInputCode.MEMORY},
    GPUInstruction.GMVI: {'I': 1, 'J': GPUBufferCode.TRANSLATION_MATRIX_OUT, 'X': GPUInputCode.IMMEDIATE, 'Y': GPUInputCode.IMMEDIATE},
}


def main():
    # build_signals_32bit()
    # build_gpu_image_decoder()
    # build_control_unit()
    # build_gpu_control_unit()
    # build_gpu_screen_encoder()
    build_color_lights_row()
    # build_signals_80_wide()
    print('Done')


def build_rom(code: List[int], sprites: List[str]) -> str:
    obj = decode('dual_rom')
    index = partition(obj)
    rom, gpu_rom, *_ = group_by(index, lambda x, y, _: 0 if x < 32 else 1)

    # Index signals
    rom_index = {pos: signal_index(e) for pos, e in rom.items()}
    gpu_rom_index = {pos: signal_index(e) for pos, e in gpu_rom.items()}

    # Map memory space onto physical space
    for address, word in enumerate(code):
        for port_x, value in enumerate((utils.signed_bitfield_64_to_32(word, 0, 32), utils.signed_bitfield_64_to_32(word, 32, 32))):
            index = address
            index, row_index_y = index // 20, index % 20
            index, row_minor_y = index // 4, index % 4
            index, col_major_x = index // 16, index % 16
            index, row_major_y = index // 6, index % 6

            assert index == 0, 'Address out of bounds for memory size'

            signal = rom_index[(port_x * 16) + col_major_x, (row_major_y * 6) + row_minor_y]
            signal = signal[row_index_y]
            signal['count'] = int(value)

    min_x, min_y = min(x for x, _ in gpu_rom_index.keys()), min(y for _, y in gpu_rom_index.keys())
    for address, sprite in enumerate(sprites):
        index = address
        index, col_x = index // 16, index % 16
        index, row_y = index // 4, index % 4

        assert index == 0, 'Address out of bounds for GPU memory size'

        buffer = ImageBuffer.unpack(sprite)
        for y in range(32):
            value = int32(0)
            for x in range(32):
                value |= (int32(1) if buffer[x, y] == '#' else int32(0)) << int32(x)

            signal = gpu_rom_index[min_x + col_x, min_y + row_y + (y >= 20)]
            signal = signal[y % 20]
            signal['count'] = int(value)

    return blueprint.encode_blueprint_string(obj)

def build_control_unit():
    obj = decode('prototype_control_unit')
    index = partition(obj)

    for row in range(4):
        for col in range(16):
            opcode = row * 16 + col
            try:
                op = Opcodes(opcode)
            except ValueError:
                continue
            cc = index[col, row * 3]
            dc = index[col, row * 3 + 1]

            assert cc['name'] == 'constant-combinator'
            assert dc['name'] == 'decider-combinator'

            if 'control_behavior' not in cc:
                cc['control_behavior'] = {}

            cc_control = cc['control_behavior']
            cc_control['filters'] = [
                constant_signal(c, 0, 1 + i) for i, c in enumerate(op.name.ljust(4))
            ] + [
                constant_signal(signal, value, 11 + i) for i, (signal, value) in enumerate(INSTRUCTIONS[op].items())
            ]

            dc_control = dc['control_behavior']['decider_conditions']
            dc_control['first_signal']['name'] = 'signal-O'
            dc_control['constant'] = opcode

    encode('control_unit', obj)

def build_gpu_control_unit():
    obj = decode('prototype_gpu_control_unit')
    index = partition(obj)

    for col in range(8):
        opcode = GPUInstruction(col)
        cc = index[col, 0]
        dc = index[col, 1]

        assert cc['name'] == 'constant-combinator'
        assert dc['name'] == 'decider-combinator'

        if 'control_behavior' not in cc:
            cc['control_behavior'] = {}

        cc_control = cc['control_behavior']
        cc_control['filters'] = [
            constant_signal(c, 0, 1 + i) for i, c in enumerate(opcode.name.ljust(4))
        ] + [
            constant_signal(signal, value, 11 + i) for i, (signal, value) in enumerate(GPU_INSTRUCTIONS[opcode].items())
        ]

        dc_control = dc['control_behavior']['decider_conditions']
        dc_control['first_signal']['name'] = 'signal-G'
        dc_control['constant'] = opcode

    encode('gpu_control_unit', obj)


def build_gpu_image_decoder():
    obj = decode('prototype_gpu_image_decoder')
    index = partition(obj)

    for y in range(6):
        for x in range(1 << y):
            e = index[x + 2, y + 1]
            control = e['control_behavior']['arithmetic_conditions']
            control['first_signal']['name'] = 'signal-Q'
            control['second_constant'] = (1 << (5 - y)) * x
            control['output_signal']['name'] = SIGNALS_32BIT[x]

    encode('gpu_image_decoder', obj)


def build_gpu_screen_encoder():
    obj = decode('prototype_gpu_screen_encoder')
    index = partition(obj)

    for x in range(31):
        e = index[x, 0]
        control = e['control_behavior']['arithmetic_conditions']
        assert control['second_constant'] == int32(1) << int32(x)


def build_color_lights_row():
    obj = decode('prototype_color_lights_row')
    index = partition(obj)
    for i in range(80):
        lhs, ac, rhs = index[i * 3, 0], index[i * 3 + 1, 1], index[i * 3 + 2, 0]

        assert lhs['name'] == 'small-lamp'
        assert ac['name'] == 'arithmetic-combinator'
        assert rhs['name'] == 'small-lamp'

        signal = SIGNALS_80[i]

        lhs['control_behavior']['circuit_condition']['first_signal']['name'] = signal
        ac['control_behavior']['arithmetic_conditions']['second_signal']['name'] = signal
        rhs['control_behavior']['circuit_condition']['first_signal']['name'] = signal

    encode('color_lights_row', obj)


def build_signals_32bit():
    obj = decode('lights_column')
    index: Dict[Tuple[int, int], Any] = partition(obj)
    column: List[Any] = [index[0, i] for i in range(32)]
    signals: List[str] = []
    for e in column:
        control = e['control_behavior']['circuit_condition']['first_signal']
        assert control['type'] == 'item'
        signals.append(control['name'])
    print(signals)

def build_signals_80_wide():
    obj = decode('dual_rom')
    index = partition(obj)
    x = []
    for i in range(4):
        x += [index[0, i]['control_behavior']['filters'][j]['signal']['name'] for j in range(20)]
    print(x)


def constant_signal(letter: str, count: IntLike, index: int):
    return {
        'signal': virtual_signal(letter),
        'count': count.value if isinstance(count, IntEnum) else count,
        'index': index
    }


def virtual_signal(letter: str) -> Any:
    return {
        'type': 'virtual',
        'name': 'signal-%s' % ('blue' if letter == ' ' else letter.upper())
    }


def partition(obj: Any) -> Dict[Tuple[int, int], Any]:
    entities = obj['blueprint']['entities']
    x_positions, y_positions = set(), set()

    for e in entities:
        pos = e['position']
        x_positions.add(pos['x'])
        y_positions.add(pos['y'])

    x_index = {x: i for i, x in enumerate(sorted(x_positions))}
    y_index = {y: i for i, y in enumerate(sorted(y_positions))}

    index = {}
    for e in entities:
        pos = e['position']
        index[x_index[pos['x']], y_index[pos['y']]] = e

    return index

def group_by(index: Dict[Tuple[int, int], Any], f: Callable[[int, int, Any], Any]) -> Tuple[Dict[Tuple[int, int], Any], ...]:
    groups = {}
    for pos, c in index.items():
        g = f(*pos, c)
        if g not in groups:
            groups[g] = {}
        groups[g][pos] = c
    return tuple(groups[g] for g in sorted(groups.keys()))

def signal_index(obj: Any) -> Dict[int, Any]:
    return {f['index'] - 1: f for f in obj['control_behavior']['filters']}


def decode(name: str, save: bool = False):
    with open('./blueprints/%s.blueprint' % name, 'r', encoding='utf-8') as f:
        bp = f.read()

    js = blueprint.decode_blueprint_string(bp)

    if save:
        os.makedirs('./blueprints/generated', exist_ok=True)
        with open('./blueprints/generated/%s.blueprint.json' % name, 'w', encoding='utf-8') as f:
            json.dump(js, f, indent=2)

    return js

def encode(name: str, obj: Any):
    os.makedirs('./blueprints/generated', exist_ok=True)
    bp = blueprint.encode_blueprint_string(obj)
    with open('./blueprints/generated/%s.blueprint' % name, 'w', encoding='utf-8') as f:
        f.write(bp)


if __name__ == '__main__':
    main()
