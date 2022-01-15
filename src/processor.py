# This is a hardware level model of the ProcessorV5 architecture
# The purpose is to be able to simulate the processor architecture before implementing it in the target medium (Factorio combinators)

from typing import List, Tuple, Dict, Callable, NamedTuple
from constants import Opcodes, Registers

import utils


class IRData(NamedTuple):
    opcode: int
    imm26: int
    op1: int
    op2: int
    op3: int
    branch: int

class OperandData(NamedTuple):
    addr: int
    offset: int
    indirect: int


class Processor:

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
        self.error_code = 0

    def load(self, instructions: List[int]):
        for i, inst in enumerate(instructions):
            self.instructions[i] = inst

    def run(self):
        self.running = True
        self.pc = 0
        while self.running:
            ir = self.inst_get()
            ir_data: IRData = decode_ir(ir)
            self.pc_next = self.pc + 1
            inst = INSTRUCTIONS[ir_data.opcode]
            inst.exec(self, ir_data)  # writes to memory
            self.pc = self.pc_next  # writes to pc

    def branch_to(self, offset: int):
        self.pc_next = self.pc + offset

    def call(self, offset: int):
        self.mem_set(Registers.RA, self.pc_next)
        self.pc_next = self.pc + offset

    def ret(self):
        self.pc_next = self.mem_get(Registers.RA)

    def halt(self):
        self.running = False

    def do_assert(self):
        addr, expected = self.asserts[self.pc]
        actual = self.mem_get_operand(addr)
        if actual != expected:
            self.assert_handle(self)
            self.running = False

    def error(self, code: int):
        self.error_code = code
        self.running = False

    def mem_get_operand(self, operand: int) -> int:
        """
        Perform a memory access using an instruction operand
        Requires two 'read' channels in order to account for offset
        """
        op = decode_operand(operand)
        value = self.mem_get(op.addr)
        if op.indirect == 1:
            return self.mem_get(value + op.offset)
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
        op = decode_operand(operand)
        if op.indirect:
            indirect = self.mem_get(op.addr)
            self.mem_set(indirect + op.offset, value)
        else:
            self.mem_set(op.addr, value)

    def mem_set(self, addr: int, value: int):
        """
        Perform a direct memory write
        Requires the singular 'write' channel
        """
        addr = addr & utils.mask(8)
        if addr != Registers.R0:  # Non-writable
            self.memory[addr] = value & utils.mask(32)

    def inst_get(self):
        """
        Perform an instruction read
        """
        return self.instructions[self.pc & utils.mask(12)]


def decode_ir(ir: int) -> IRData:
    return IRData(
        utils.bitfield(ir, 58, 6),
        utils.signed_bitfield(ir, 32, 26),
        utils.bitfield(ir, 32, 16),
        utils.bitfield(ir, 16, 16),
        utils.bitfield(ir, 0, 16),
        utils.signed_bitfield(ir, 16, 16)
    )


def decode_operand(operand: int) -> OperandData:
    return OperandData(
        utils.bitfield(operand, 6, 10),
        utils.signed_bitfield(operand, 1, 5),
        utils.bit(operand, 0)
    )


class Instruction:

    def __init__(self, index: Opcodes):
        self.opcode = index

    def exec(self, model: Processor, ir: IRData):
        raise NotImplementedError


class ArithmeticInstruction(Instruction):
    def __init__(self, index: Opcodes, action: Callable[[int, int], int]):  # (Y, Z) -> X
        super().__init__(index)
        self.action = action

    def exec(self, model: Processor, ir: IRData):
        model.mem_set_operand(ir.op2, self.action(model.mem_get_operand(ir.op1), model.mem_get_operand(ir.op3)))

class ArithmeticImmediateInstruction(Instruction):
    def __init__(self, index: Opcodes, action: Callable[[int, int], int]):  # (Y, #Z) -> X
        super().__init__(index)
        self.action = action

    def exec(self, model: Processor, ir: IRData):
        model.mem_set_operand(ir.op2, self.action(model.mem_get_operand(ir.op3), ir.imm26))

class BranchInstruction(Instruction):
    def __init__(self, index: Opcodes, comparator: Callable[[int, int], bool]):  # (X ? Y)
        super().__init__(index)
        self.comparator = comparator

    def exec(self, model: Processor, ir: IRData):
        if self.comparator(model.mem_get_operand(ir.op3), model.mem_get_operand(ir.op1)):
            model.branch_to(ir.branch)

class BranchImmediateInstruction(Instruction):
    def __init__(self, index: Opcodes, comparator: Callable[[int, int], bool]):  # (X ? #Y)
        super().__init__(index)
        self.comparator = comparator

    def exec(self, model: Processor, ir: IRData):
        if self.comparator(model.mem_get_operand(ir.op3), ir.imm26):
            model.branch_to(ir.branch)

class SpecialInstruction(Instruction):
    def __init__(self, index: Opcodes, method: Callable[[Processor, IRData], None]):
        super().__init__(index)
        self.method = method

    def exec(self, model: Processor, ir: IRData):
        self.method(model, ir)

class InvalidInstruction(Instruction):
    def __init__(self, error: Opcodes):
        super().__init__(error)

    def exec(self, model: Processor, ir: IRData):
        model.error(self.opcode)


def validate(*instructions: Instruction) -> Tuple[Instruction]:
    for i, inst in enumerate(instructions):
        assert i == inst.opcode.value, 'Validation Problem: Instruction %s has opcode %s but is at index %d' % (type(inst), repr(inst.opcode), i)
    return instructions


INSTRUCTIONS: Tuple[Instruction] = validate(
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
    ArithmeticImmediateInstruction(Opcodes.RSI, lambda y, imm: y >> imm),
    ArithmeticImmediateInstruction(Opcodes.LSIR, lambda y, imm: imm << y),
    ArithmeticImmediateInstruction(Opcodes.RSIR, lambda y, imm: imm >> y),
    ArithmeticImmediateInstruction(Opcodes.EQI, lambda y, imm: int(y == imm)),
    ArithmeticImmediateInstruction(Opcodes.NEI, lambda y, imm: int(y != imm)),
    ArithmeticImmediateInstruction(Opcodes.LTI, lambda y, imm: int(y < imm)),
    ArithmeticImmediateInstruction(Opcodes.GTI, lambda y, imm: int(y > imm)),
    BranchInstruction(Opcodes.BEQ, lambda x, y: x == y),
    BranchInstruction(Opcodes.BNE, lambda x, y: x != y),
    BranchInstruction(Opcodes.BLT, lambda x, y: x < y),
    BranchInstruction(Opcodes.BLE, lambda x, y: x <= y),
    BranchImmediateInstruction(Opcodes.BEQI, lambda x, y: x == y),
    BranchImmediateInstruction(Opcodes.BNEI, lambda x, y: x != y),
    BranchImmediateInstruction(Opcodes.BLTI, lambda x, y: x < y),
    BranchImmediateInstruction(Opcodes.BGTI, lambda x, y: x > y),
    SpecialInstruction(Opcodes.CALL, lambda model, ir: model.call(ir.branch)),
    SpecialInstruction(Opcodes.RET, lambda model, _: model.ret()),
    SpecialInstruction(Opcodes.HALT, lambda model, _: model.halt()),
    SpecialInstruction(Opcodes.ASSERT, lambda model, _: model.do_assert())
)
