# This is a hardware level model of the ProcessorV5 architecture
# The purpose is to be able to simulate the processor architecture before implementing it in the target medium (Factorio combinators)

from typing import List, Tuple, Dict, Callable, NamedTuple
from constants import Opcodes, Registers
from numpy import int32, uint64

import utils


class IRData(NamedTuple):
    opcode: int32
    imm26: int32
    op1: int32
    op2: int32
    op3: int32
    branch: int32

class OperandData(NamedTuple):
    addr: int32
    offset: int32
    indirect: int32


class Processor:

    MEMORY_BITS = 10
    INSTRUCTION_BITS = 12

    def __init__(self, asserts: Dict[int, Tuple[int, int]] = None, assert_handle: Callable[['Processor'], None] = None):
        if asserts is None:
            asserts = {}

        self.memory: List[int32] = [int32(0)] * (1 << Processor.MEMORY_BITS)  # 256 x 32b
        self.instructions: List[uint64] = [uint64(0)] * (1 << Processor.INSTRUCTION_BITS)  # 4096 x 64b
        self.asserts: Dict[int32, Tuple[int32, int32]] = {int32(k): (int32(v[0]), int32(v[1])) for k, v in asserts.items()}
        self.assert_handle = assert_handle

        self.memory_mask: int32 = utils.mask_int32(Processor.MEMORY_BITS)
        self.instruction_mask: int32 = utils.mask_int32(Processor.INSTRUCTION_BITS)

        self.running = False
        self.pc = int32(0)
        self.pc_next = int32(0)
        self.error_code = int32(0)

    def load(self, instructions: List[int]):
        for i, inst in enumerate(instructions):
            self.instructions[i] = uint64(inst)

    def run(self):
        self.running = True
        self.pc = int32(0)
        while self.running:
            ir = self.inst_get()
            ir_data: IRData = decode_ir(ir)
            self.pc_next = self.pc + int32(1)
            inst = INSTRUCTIONS[ir_data.opcode]
            inst.exec(self, ir_data)  # writes to memory
            self.pc = self.pc_next  # writes to pc

    def branch_to(self, offset: int32):
        self.pc_next = self.pc + offset

    def call(self, offset: int32):
        self.mem_set(int32(Registers.RA), self.pc_next)
        self.pc_next = self.pc + offset

    def ret(self):
        self.pc_next = self.mem_get(int32(Registers.RA))

    def halt(self):
        self.running = False

    def do_assert(self):
        addr, expected = self.asserts[self.pc]
        actual = self.mem_get_operand(addr)
        if actual != expected:
            self.assert_handle(self)
            self.running = False

    def error(self, code: int32):
        self.error_code = code
        self.running = False

    def mem_get_operand(self, operand: int32) -> int32:
        """
        Perform a memory access using an instruction operand
        Requires two 'read' channels in order to account for offset
        """
        op = decode_operand(operand)
        value = self.mem_get(op.addr)
        if op.indirect == int32(1):
            return self.mem_get(value + op.offset)
        else:
            return value

    def mem_get(self, addr: int32) -> int32:
        """
        Perform a direct memory access
        Requires one 'read' channel
        """
        return self.memory[addr & self.memory_mask]

    def mem_set_operand(self, operand: int32, value: int32):
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

    def mem_set(self, addr: int32, value: int32):
        """
        Perform a direct memory write
        Requires the singular 'write' channel
        """
        addr = addr & self.memory_mask
        if addr != Registers.R0:  # Non-writable
            self.memory[addr] = value

    def inst_get(self) -> uint64:
        """
        Perform an instruction read
        """
        return self.instructions[self.pc & self.instruction_mask]


def decode_ir(ir: uint64) -> IRData:
    return IRData(
        int32(utils.bitfield_uint64(ir, 58, 6)),
        utils.signed_bitfield_64_to_32(ir, 32, 26),
        int32(utils.bitfield_uint64(ir, 32, 16)),
        int32(utils.bitfield_uint64(ir, 16, 16)),
        int32(utils.bitfield_uint64(ir, 0, 16)),
        utils.signed_bitfield_64_to_32(ir, 16, 16)
    )


def decode_operand(operand: int32) -> OperandData:
    return OperandData(
        utils.bitfield_int32(operand, 6, 10),
        utils.signed_bitfield_32(operand, 1, 5),
        utils.bit_int32(operand, 0)
    )


class Instruction:

    def __init__(self, index: Opcodes):
        self.opcode = index

    def exec(self, model: Processor, ir: IRData):
        raise NotImplementedError


class ArithmeticInstruction(Instruction):
    def __init__(self, index: Opcodes, action: Callable[[int32, int32], int32]):  # (Y, Z) -> X
        super().__init__(index)
        self.action = action

    def exec(self, model: Processor, ir: IRData):
        model.mem_set_operand(ir.op2, self.action(model.mem_get_operand(ir.op1), model.mem_get_operand(ir.op3)))

class ArithmeticImmediateInstruction(Instruction):
    def __init__(self, index: Opcodes, action: Callable[[int32, int32], int32]):  # (Y, #Z) -> X
        super().__init__(index)
        self.action = action

    def exec(self, model: Processor, ir: IRData):
        model.mem_set_operand(ir.op2, self.action(model.mem_get_operand(ir.op3), ir.imm26))

class BranchInstruction(Instruction):
    def __init__(self, index: Opcodes, comparator: Callable[[int32, int32], bool]):  # (X ? Y)
        super().__init__(index)
        self.comparator = comparator

    def exec(self, model: Processor, ir: IRData):
        if self.comparator(model.mem_get_operand(ir.op3), model.mem_get_operand(ir.op1)):
            model.branch_to(ir.branch)

class BranchImmediateInstruction(Instruction):
    def __init__(self, index: Opcodes, comparator: Callable[[int32, int32], bool]):  # (X ? #Y)
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
        model.error(int32(self.opcode.value))


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
    ArithmeticInstruction(Opcodes.NAND, lambda y, z: ~(y & z)),
    ArithmeticInstruction(Opcodes.NOR, lambda y, z: ~(y | z)),
    ArithmeticInstruction(Opcodes.XOR, lambda y, z: y ^ z),
    ArithmeticInstruction(Opcodes.XNOR, lambda y, z: ~(y ^ z)),
    ArithmeticInstruction(Opcodes.LS, lambda y, z: y << z),
    ArithmeticInstruction(Opcodes.RS, lambda y, z: y >> z),
    ArithmeticInstruction(Opcodes.EQ, lambda y, z: int32(y == z)),
    ArithmeticInstruction(Opcodes.NE, lambda y, z: int32(y != z)),
    ArithmeticInstruction(Opcodes.LT, lambda y, z: int32(y < z)),
    ArithmeticInstruction(Opcodes.LE, lambda y, z: int32(y <= z)),
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
    ArithmeticImmediateInstruction(Opcodes.NANDI, lambda y, imm: ~(y & imm)),
    ArithmeticImmediateInstruction(Opcodes.NORI, lambda y, imm: ~(y | imm)),
    ArithmeticImmediateInstruction(Opcodes.XORI, lambda y, imm: y ^ imm),
    ArithmeticImmediateInstruction(Opcodes.XNORI, lambda y, imm: ~(y ^ imm)),
    ArithmeticImmediateInstruction(Opcodes.LSI, lambda y, imm: y << imm),
    ArithmeticImmediateInstruction(Opcodes.RSI, lambda y, imm: y >> imm),
    ArithmeticImmediateInstruction(Opcodes.LSIR, lambda y, imm: imm << y),
    ArithmeticImmediateInstruction(Opcodes.RSIR, lambda y, imm: imm >> y),
    ArithmeticImmediateInstruction(Opcodes.EQI, lambda y, imm: int32(y == imm)),
    ArithmeticImmediateInstruction(Opcodes.NEI, lambda y, imm: int32(y != imm)),
    ArithmeticImmediateInstruction(Opcodes.LTI, lambda y, imm: int32(y < imm)),
    ArithmeticImmediateInstruction(Opcodes.GTI, lambda y, imm: int32(y > imm)),
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
