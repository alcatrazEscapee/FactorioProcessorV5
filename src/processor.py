# This is a hardware level model of the ProcessorV5 architecture
# The purpose is to be able to simulate the processor architecture before implementing it in the target medium (Factorio combinators)

from typing import List, Tuple, Dict, Callable
from constants.opcodes import Opcodes

import utils


class Processor:

    # Marked memory locations
    SP = 1023
    RA = 1022
    RV = 1021
    R0 = 0

    def __init__(self, asserts: Dict[int, Tuple[int, int]] = None, assert_handle: Callable[['Processor'], None] = None):
        if asserts is None:
            asserts = {}

        self.memory = [0] * (1 << 10)  # 256 x 32b
        self.instructions = [0] * (1 << 12)  # 4096 x 64b
        self.asserts = asserts
        self.assert_handle = assert_handle

        self.running = False
        self.pc = 0
        self.pc_next = 0

    def load(self, instructions: List[int]):
        self.instructions = [0] * (1 << 12)
        for i, inst in enumerate(instructions):
            self.instructions[i] = inst

    def run(self):
        self.running = True
        self.pc = 0
        while self.running:
            ir = self.inst_get()
            ir_opcode, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch = decode_ir(ir)
            self.pc_next = self.pc + 1
            inst = INSTRUCTIONS[ir_opcode]
            inst.exec(self, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch)  # writes to memory
            self.pc = self.pc_next  # writes to pc
        print('Done')

    def branch_to(self, offset: int):
        self.pc_next = self.pc + offset

    def call(self, offset: int):
        self.mem_set(Processor.RA, self.pc_next)
        self.pc_next = self.pc + offset

    def ret(self):
        self.pc_next = self.mem_get(Processor.RA)

    def halt(self):
        print('Halt')
        self.running = False

    def do_assert(self):
        addr, expected = self.asserts[self.pc]
        actual = self.mem_get_operand(addr)
        if actual != expected:
            self.assert_handle(self)
            self.running = False

    def error(self, code: int):
        print('System Error: %d' % code)
        self.running = False

    def mem_get_operand(self, operand: int) -> int:
        """
        Perform a memory access using an instruction operand
        Requires two 'read' channels in order to account for offset
        """
        operand_addr, operand_indirect, operand_offset = decode_operand(operand)
        value = self.mem_get(operand_addr)
        if operand_indirect == 1:
            return self.mem_get(value + operand_offset)
        else:
            return value

    def mem_get(self, addr: int) -> int:
        """
        Perform a direct memory access
        Requires one 'read' channel
        """
        return self.memory[addr & utils.mask(8)]

    def mem_set_operand(self, operand: int, value: int):
        """
        Perform a memory write using an instruction operand
        Requires a 'read' channel and the singular 'write' channel
        """
        operand_addr, operand_indirect, operand_offset = decode_operand(operand)
        if operand_indirect:
            indirect = self.mem_get(operand_addr)
            self.mem_set(indirect + operand_offset, value)
        else:
            self.mem_set(operand_addr, value)

    def mem_set(self, addr: int, value: int):
        """
        Perform a direct memory write
        Requires the singular 'write' channel
        """
        addr = addr & ((1 << 8) - 1)
        if addr != Processor.R0:  # Deny writing to R0 (simulate non connection)
            self.memory[addr] = value & utils.mask(32)

    def inst_get(self):
        """
        Perform an instruction read
        """
        return self.instructions[self.pc & utils.mask(12)]


class Instruction:

    def __init__(self, index: int):
        self.index = index

    def exec(self, model: Processor, ir_imm26: int, ir_op1: int, ir_op2: int, ir_op3: int, ir_branch: int):
        pass


class ArithmeticInstruction(Instruction):
    def __init__(self, index: int, action: Callable[[int, int], int]):  # (Y, Z) -> X
        super().__init__(index)
        self.action = action

    def exec(self, model: Processor, ir_imm26: int, ir_op1: int, ir_op2: int, ir_op3: int, ir_branch: int):
        model.mem_set_operand(ir_op2, self.action(model.mem_get_operand(ir_op1), model.mem_get_operand(ir_op3)))


class ArithmeticImmediateInstruction(Instruction):
    def __init__(self, index: int, action: Callable[[int, int], int]):  # (Y, #Z) -> X
        super().__init__(index)
        self.action = action

    def exec(self, model: Processor, ir_imm26: int, ir_op1: int, ir_op2: int, ir_op3: int, ir_branch: int):
        model.mem_set_operand(ir_op2, self.action(model.mem_get_operand(ir_op3), ir_imm26))


class BranchInstruction(Instruction):
    def __init__(self, index: int, comparator: Callable[[int, int], bool]):  # (X ? Y)
        super().__init__(index)
        self.comparator = comparator

    def exec(self, model: Processor, ir_imm26: int, ir_op1: int, ir_op2: int, ir_op3: int, ir_branch: int):
        if self.comparator(model.mem_get_operand(ir_op2), model.mem_get_operand(ir_op1)):
            model.branch_to(ir_branch)


class BranchImmediateInstruction(Instruction):
    def __init__(self, index: int, comparator: Callable[[int, int], bool]):  # (X ? #Y)
        super().__init__(index)
        self.comparator = comparator

    def exec(self, model: Processor, ir_imm26: int, ir_op1: int, ir_op2: int, ir_op3: int, ir_branch: int):
        if self.comparator(model.mem_get_operand(ir_op2), ir_imm26):
            model.branch_to(ir_branch)


class SpecialInstruction(Instruction):
    def __init__(self, index: int, method: Callable[[Processor, int, int, int, int, int], None]):
        super().__init__(index)
        self.method = method

    def exec(self, model: Processor, ir_imm26: int, ir_op1: int, ir_op2: int, ir_op3: int, ir_branch: int):
        self.method(model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch)


class InvalidInstruction(Instruction):
    def __init__(self, error: int):
        super().__init__(error)

    def exec(self, model: Processor, ir_imm26: int, ir_op1: int, ir_op2: int, ir_op3: int, ir_branch: int):
        model.error(self.index)


INSTRUCTIONS: List[Instruction] = [
    ArithmeticInstruction(Opcodes.ADD, lambda y, z: y + z),
    ArithmeticInstruction(Opcodes.SUB, lambda y, z: y - z),
    ArithmeticInstruction(Opcodes.MUL, lambda y, z: y * z),
    ArithmeticInstruction(Opcodes.DIV, lambda y, z: y // z),
    ArithmeticInstruction(Opcodes.POW, lambda y, z: y ** z),
    ArithmeticInstruction(Opcodes.MOD, lambda y, z: y % z),
    ArithmeticInstruction(Opcodes.AND, lambda y, z: y & z),
    ArithmeticInstruction(Opcodes.OR, lambda y, z: y | z),
    ArithmeticInstruction(Opcodes.NAND, lambda y, z: utils.invert(y & z, 32)),
    ArithmeticInstruction(Opcodes.NOR, lambda y, z: utils.invert(y | z, 32)),
    ArithmeticInstruction(Opcodes.XOR, lambda y, z: y ^ z),
    ArithmeticInstruction(Opcodes.XNOR, lambda y, z: utils.invert(y ^ z, 32)),
    ArithmeticInstruction(Opcodes.LS, lambda y, z: y << z),
    ArithmeticInstruction(Opcodes.RS, lambda y, z: y >> z),
    ArithmeticInstruction(Opcodes.EQ, lambda y, z: int(y == z)),
    ArithmeticInstruction(Opcodes.NE, lambda y, z: int(y != z)),
    ArithmeticInstruction(Opcodes.LT, lambda y, z: int(y < z)),
    ArithmeticInstruction(Opcodes.LE, lambda y, z: int(y <= z)),
    ArithmeticImmediateInstruction(Opcodes.ADDI, lambda y, imm: y + imm),
    ArithmeticImmediateInstruction(Opcodes.SUBIR, lambda y, imm: imm - y),
    ArithmeticImmediateInstruction(Opcodes.MULI, lambda y, imm: y * imm),
    ArithmeticImmediateInstruction(Opcodes.DIVI, lambda y, imm: y / imm),
    ArithmeticImmediateInstruction(Opcodes.DIVIR, lambda y, imm: imm / y),
    ArithmeticImmediateInstruction(Opcodes.POWI, lambda y, imm: y ** imm),
    ArithmeticImmediateInstruction(Opcodes.POWIR, lambda y, imm: imm ** y),
    ArithmeticImmediateInstruction(Opcodes.MODI, lambda y, imm: y % imm),
    ArithmeticImmediateInstruction(Opcodes.MODIR, lambda y, imm: imm % y),
    ArithmeticImmediateInstruction(Opcodes.ANDI, lambda y, imm: y & imm),
    ArithmeticImmediateInstruction(Opcodes.ORI, lambda y, imm: y | imm),
    ArithmeticImmediateInstruction(Opcodes.NANDI, lambda y, imm: utils.invert(y & imm, 32)),
    ArithmeticImmediateInstruction(Opcodes.NORI, lambda y, imm: utils.invert(y | imm, 32)),
    ArithmeticImmediateInstruction(Opcodes.XORI, lambda y, imm: y ^ imm),
    ArithmeticImmediateInstruction(Opcodes.XNORI, lambda y, imm: utils.invert(y ^ imm, 32)),
    ArithmeticImmediateInstruction(Opcodes.LSI, lambda y, imm: y << imm),
    ArithmeticImmediateInstruction(Opcodes.LSIR, lambda y, imm: imm << y),
    ArithmeticImmediateInstruction(Opcodes.RSI, lambda y, imm: y >> imm),
    ArithmeticImmediateInstruction(Opcodes.RSIR, lambda y, imm: imm >> y),
    ArithmeticImmediateInstruction(Opcodes.EQ, lambda y, imm: int(y == imm)),
    ArithmeticImmediateInstruction(Opcodes.NE, lambda y, imm: int(y != imm)),
    ArithmeticImmediateInstruction(Opcodes.LT, lambda y, imm: int(y < imm)),
    ArithmeticImmediateInstruction(Opcodes.LE, lambda y, imm: int(y <= imm)),
    BranchInstruction(Opcodes.BEQ, lambda x, y: x == y),
    BranchInstruction(Opcodes.BNE, lambda x, y: x != y),
    BranchInstruction(Opcodes.BLT, lambda x, y: x < y),
    BranchInstruction(Opcodes.BLE, lambda x, y: x <= y),
    BranchImmediateInstruction(Opcodes.BEQI, lambda x, y: x == y),
    BranchImmediateInstruction(Opcodes.BNEI, lambda x, y: x != y),
    BranchImmediateInstruction(Opcodes.BLTI, lambda x, y: x < y),
    BranchImmediateInstruction(Opcodes.BGTI, lambda x, y: x > y),
    SpecialInstruction(Opcodes.CALL, lambda model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch: model.call()),
    SpecialInstruction(Opcodes.RET, lambda model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch: model.ret()),
    SpecialInstruction(Opcodes.HALT, lambda model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch: model.halt()),
    SpecialInstruction(Opcodes.ASSERT, lambda model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch: model.do_assert())
]


def decode_ir(ir: int) -> Tuple[int, int, int, int, int, int]:
    return utils.bitfield(ir, 58, 6), utils.signed_bitfield(ir, 32, 26), utils.bitfield(ir, 32, 16), utils.bitfield(ir, 16, 16), utils.bitfield(ir, 0, 16), utils.signed_bitfield(ir, 0, 13)


def decode_operand(operand: int) -> Tuple[int, int, int]:
    return utils.bitfield(operand, 8, 8), utils.bitfield(operand, 7, 1), utils.signed_bitfield(operand, 0, 7)

