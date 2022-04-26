from constants import Instructions, Opcodes, Registers, GPUInstruction, GPUFunction, GPUImageDecoder
from numpy import int32, uint64
from typing import List, Sequence, Tuple

import processor


def decode(code: List[int], print_table: Sequence[Tuple[str, Tuple[int, ...]]] | None = None) -> List[str]:
    decoded = []
    for i, c in enumerate(code):
        if c is None:
            decoded.append('---')
            continue

        fields = processor.decode_ir(uint64(c))
        op = Opcodes(fields.opcode)
        op_name = op.name.lower()
        if c == 0:  # Special case, this is a implicit (and explicitly generated) noop
            op_name = 'noop'
        inst = '%04d | %s' % (i, op_name)

        if c == 0:  # noop
            pass
        elif op.value <= Opcodes.LE.value:  # Type A
            inst += ' ' + decode_address(fields.op2) + ' ' + decode_address(fields.op1) + ' ' + decode_address(fields.op3)
        elif op.value <= Opcodes.GTI.value:  # Type B
            inst += ' ' + decode_address(fields.op2) + ' ' + decode_address(fields.op3) + ' ' + str(fields.imm26)
        elif op.value <= Opcodes.BLE.value:  # Type C
            inst += ' ' + decode_address(fields.op1) + ' ' + decode_address(fields.op3) + ' ' + decode_offset(i, fields.branch)
        elif op.value <= Opcodes.BGTI.value:  # Type D
            inst += ' ' + decode_address(fields.op3) + ' ' + str(fields.imm26) + ' ' + decode_offset(i, fields.branch)
        elif op == Opcodes.HALT or op == Opcodes.RET:
            pass
        elif op == Opcodes.CALL:
            inst += ' ' + decode_offset(i, fields.branch)
        elif op == Opcodes.ASSERT:
            inst += ' ' + decode_address(fields.op3) + ' = ' + str(fields.imm26)
        elif op == Opcodes.PRINT:
            inst += ' print ['
            if print_table is not None:
                format_string, ops = print_table[fields.print_index]
                inst += ' "' + format_string + '" ' + ' '.join([decode_address(op) for op in ops])
            inst += ' ]'
        elif op == Opcodes.GPU:
            gpu = GPUInstruction(fields.gpu_opcode)
            inst = '%04d | %s' % (i, Instructions[gpu.name].value)
            if gpu == GPUInstruction.GLSI:
                inst += ' ' + str(fields.op1)
            elif gpu == GPUInstruction.GLS:
                inst += ' ' + decode_address(fields.op1)
            elif gpu == GPUInstruction.GLSD:
                inst += ' ' + decode_address(fields.op1) + ' ' + GPUImageDecoder(fields.gpu_function).name
            elif gpu == GPUInstruction.GCB or gpu == GPUInstruction.GCI:
                inst += ' ' + GPUFunction(fields.gpu_function).name
            elif gpu == GPUInstruction.GMV:
                inst += ' ' + decode_address(fields.op1) + ' ' + decode_address(fields.op3)
            elif gpu == GPUInstruction.GMVI:
                inst += ' ' + str(fields.op1) + ' ' + str(fields.op3)
        else:
            raise NotImplementedError

        decoded.append(inst)
    return decoded


def decode_address(value: int32) -> str:
    op = processor.decode_operand(value)
    indirect = '@' if op.indirect == 1 else ''
    offset = '.%d' % op.offset if op.offset != 0 else ''
    if 0 <= op.addr <= Registers.R16:  # Infer register argument
        address = 'r%d' % op.addr
    elif op.addr == Registers.SP:
        address = 'sp'
    elif op.addr == Registers.RA:
        address = 'ra'
    elif op.addr == Registers.RV:
        address = 'rv'
    else:
        address = '@%d' % op.addr
    return indirect + address + offset

def decode_offset(code: int, offset: int) -> str:
    return '[+%s -> %s]' % (offset, code + offset)
