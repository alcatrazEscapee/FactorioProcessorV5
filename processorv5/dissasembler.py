from typing import List
from constants import Instructions, Opcodes, GPUInstruction, GPUFunction
from numpy import int32, uint64

import processor


def decode(code: List[int]) -> List[str]:
    decoded = []
    for i, c in enumerate(code):
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
            inst += ' ' + decode_address(fields.op1) + ' ' + decode_address(fields.op3) + ' [' + str(fields.branch + i) + ']'
        elif op.value <= Opcodes.BGTI.value:  # Type D
            inst += ' ' + decode_address(fields.op3) + ' ' + str(fields.imm26) + ' [' + str(fields.branch + i) + ']'
        elif op == Opcodes.HALT or op == Opcodes.RET:
            pass
        elif op == Opcodes.ASSERT:
            inst += ' <synthetic>'
        elif op == Opcodes.GPU:
            gpu = GPUInstruction(fields.gpu_opcode)
            inst = '%04d | %s' % (i, Instructions[gpu.name].value)
            if gpu == GPUInstruction.GLSI:
                inst += ' ' + str(fields.op1)
            elif gpu == GPUInstruction.GLSM:
                inst += ' ' + decode_address(fields.op1)
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
    return '@%s%d%s' % (
        '@' if op.indirect == 1 else '',
        op.addr,
        '.%d' % op.offset if op.offset != 0 else ''
    )
