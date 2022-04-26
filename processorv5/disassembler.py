from constants import Instructions, Opcodes, Registers, GPUInstruction, GPUFunction, GPUImageDecoder
from numpy import int32, uint64
from typing import List, Sequence, Tuple, Dict

import processor


def decode(code: List[int], print_table: Sequence[Tuple[str, Tuple[int, ...]]] | None = None, memory_table: Dict[int, str] | None = None, label_table: Dict[int, str] | None = None) -> List[str]:
    return Disassembler(code, print_table, memory_table, label_table).decode()


class Disassembler:

    def __init__(self, code: List[int], print_table: Sequence[Tuple[str, Tuple[int, ...]]] | None = None, memory_table: Dict[int, str] | None = None, label_table: Dict[int, str] | None = None):
        self.code = code

        # Debug Symbols
        self.print_table = print_table
        self.memory_table = memory_table
        self.label_table = label_table

    def decode(self) -> List[str]:
        decoded = []
        for i, c in enumerate(self.code):
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
                inst += ' ' + self.decode_address(fields.op2) + ' ' + self.decode_address(fields.op1) + ' ' + self.decode_address(fields.op3)
            elif op.value <= Opcodes.GTI.value:  # Type B
                inst += ' ' + self.decode_address(fields.op2) + ' ' + self.decode_address(fields.op3) + ' ' + str(fields.imm26)
            elif op.value <= Opcodes.BLE.value:  # Type C
                inst += ' ' + self.decode_address(fields.op1) + ' ' + self.decode_address(fields.op3) + ' ' + self.decode_offset(i, fields.branch)
            elif op.value <= Opcodes.BGTI.value:  # Type D
                inst += ' ' + self.decode_address(fields.op3) + ' ' + str(fields.imm26) + ' ' + self.decode_offset(i, fields.branch)
            elif op == Opcodes.HALT or op == Opcodes.RET:
                pass
            elif op == Opcodes.CALL:
                inst += ' ' + self.decode_offset(i, fields.branch)
            elif op == Opcodes.ASSERT:
                inst += ' ' + self.decode_address(fields.op3) + ' = ' + str(fields.imm26)
            elif op == Opcodes.PRINT:
                inst += ' ['
                if self.print_table is not None:
                    format_string, ops = self.print_table[fields.print_index]
                    inst += ' "' + format_string + '" ' + ' '.join([self.decode_address(op) for op in ops])
                inst += ' ]'
            elif op == Opcodes.GPU:
                gpu = GPUInstruction(fields.gpu_opcode)
                inst = '%04d | %s' % (i, Instructions[gpu.name].value)
                if gpu == GPUInstruction.GLSI:
                    inst += ' ' + str(fields.op1)
                elif gpu == GPUInstruction.GLS:
                    inst += ' ' + self.decode_address(fields.op1)
                elif gpu == GPUInstruction.GLSD:
                    inst += ' ' + self.decode_address(fields.op1) + ' ' + GPUImageDecoder(fields.gpu_function).name
                elif gpu == GPUInstruction.GCB or gpu == GPUInstruction.GCI:
                    inst += ' ' + GPUFunction(fields.gpu_function).name
                elif gpu == GPUInstruction.GMV:
                    inst += ' ' + self.decode_address(fields.op1) + ' ' + self.decode_address(fields.op3)
                elif gpu == GPUInstruction.GMVI:
                    inst += ' ' + str(fields.op1) + ' ' + str(fields.op3)
            else:
                raise NotImplementedError

            if self.label_table is not None and i in self.label_table:
                inst += ' #%s' % self.label_table[i]

            decoded.append(inst)
        return decoded

    def decode_address(self, value: int32):
        return decode_address(value, self.memory_table)

    def decode_offset(self, code: int, offset: int):
        sign = '+' if offset >= 0 else ''
        if self.label_table is not None and code + offset in self.label_table:
            return '[%s%d -> %s]' % (sign, offset, self.label_table[code + offset])
        return '[%s%d -> %d]' % (sign, offset, code + offset)


def decode_address(value: int32, memory_table: Dict[int, str] | None = None) -> str:
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
    elif memory_table is not None and op.addr in memory_table:
        address = '@' + memory_table[op.addr]
    else:
        address = '@%d' % op.addr
    return indirect + address + offset
