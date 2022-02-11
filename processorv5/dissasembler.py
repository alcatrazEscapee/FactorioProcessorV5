from typing import List
from constants import Opcodes

import processor


def decode(code: List[int]) -> List[str]:
    decoded = []

    for i, c in enumerate(code):
        fields = processor.decode_ir(c)
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
        else:
            raise NotImplementedError

        decoded.append(inst)
    return decoded


def decode_address(value: int) -> str:
    op = processor.decode_operand(value)
    return '@%s%d%s' % (
        '@' if op.indirect == 1 else '',
        op.addr,
        '.%d' % op.offset if op.offset != 0 else ''
    )
