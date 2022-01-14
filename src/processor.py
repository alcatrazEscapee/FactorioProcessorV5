# This is a hardware level model of the ProcessorV5 architecture
# The purpose is to be able to simulate the processor architecture before implementing it in the target medium (Factorio combinators)

from typing import List, Tuple, Callable
from constants.opcodes import Opcodes


def main():
    model = Processor()
    model.instructions[0] = 0b010010_00000000000000000000000001_0000000100000000_0000000100000000
    model.instructions[1] = 0b110111_00000000000000000000000000_00000000000000000000000000000000
    model.run()


class Processor:

    # Marked memory locations
    SP = 255
    RA = 254
    RV = 253
    R0 = 0

    def __init__(self):
        self.memory = [0] * (1 << 8)  # 256 x 32b
        self.instructions = [0] * (1 << 12)  # 4096 x 64b

        self.running = False
        self.pc = 0
        self.pc_next = 0

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
        return self.memory[addr & mask(8)]

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
            self.memory[addr] = value & mask(32)

    def inst_get(self):
        """
        Perform an instruction read
        """
        return self.instructions[self.pc & mask(12)]


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
    ArithmeticInstruction(Opcodes.NAND, lambda y, z: invert(y & z, 32)),
    ArithmeticInstruction(Opcodes.NOR, lambda y, z: invert(y | z, 32)),
    ArithmeticInstruction(Opcodes.XOR, lambda y, z: y ^ z),
    ArithmeticInstruction(Opcodes.XNOR, lambda y, z: invert(y ^ z, 32)),
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
    ArithmeticImmediateInstruction(25, lambda y, imm: y % imm),
    ArithmeticImmediateInstruction(26, lambda y, imm: imm % y),
    ArithmeticImmediateInstruction(27, lambda y, imm: y & imm),
    ArithmeticImmediateInstruction(28, lambda y, imm: y | imm),
    ArithmeticImmediateInstruction(29, lambda y, imm: invert(y & imm, 32)),
    ArithmeticImmediateInstruction(30, lambda y, imm: invert(y | imm, 32)),
    ArithmeticImmediateInstruction(31, lambda y, imm: y ^ imm),
    ArithmeticImmediateInstruction(32, lambda y, imm: invert(y ^ imm, 32)),
    ArithmeticImmediateInstruction(33, lambda y, imm: y << imm),
    ArithmeticImmediateInstruction(34, lambda y, imm: imm << y),
    ArithmeticImmediateInstruction(35, lambda y, imm: y >> imm),
    ArithmeticImmediateInstruction(36, lambda y, imm: imm >> y),
    ArithmeticImmediateInstruction(37, lambda y, imm: int(y == imm)),
    ArithmeticImmediateInstruction(38, lambda y, imm: int(y != imm)),
    ArithmeticImmediateInstruction(39, lambda y, imm: int(y < imm)),
    ArithmeticImmediateInstruction(40, lambda y, imm: int(y > imm)),
    BranchInstruction(41, lambda x, y: x == y),
    BranchInstruction(42, lambda x, y: x != y),
    BranchInstruction(43, lambda x, y: x < y),
    BranchInstruction(44, lambda x, y: x <= y),
    BranchImmediateInstruction(45, lambda x, y: x == y),
    BranchImmediateInstruction(46, lambda x, y: x != y),
    BranchImmediateInstruction(47, lambda x, y: x < y),
    BranchImmediateInstruction(48, lambda x, y: x > y),
    SpecialInstruction(49, lambda model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch: model.call()),
    SpecialInstruction(50, lambda model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch: model.ret()),
    SpecialInstruction(51, lambda model, ir_imm26, ir_op1, ir_op2, ir_op3, ir_branch: model.halt()),
    InvalidInstruction(52),
    InvalidInstruction(53),
    InvalidInstruction(54),
    InvalidInstruction(55),
    InvalidInstruction(56),
    InvalidInstruction(57),
    InvalidInstruction(58),
    InvalidInstruction(59),
    InvalidInstruction(60),
    InvalidInstruction(61),
    InvalidInstruction(62),
    InvalidInstruction(63)
]


def decode_ir(ir: int) -> Tuple[int, int, int, int, int, int]:
    return bitfield(ir, 58, 6), signed_bitfield(ir, 32, 26), bitfield(ir, 32, 16), bitfield(ir, 16, 16), bitfield(ir, 0, 16), signed_bitfield(ir, 0, 13)


def decode_operand(operand: int) -> Tuple[int, int, int]:
    return bitfield(operand, 8, 8), bitfield(operand, 7, 1), signed_bitfield(operand, 0, 7)


def sign(x: int, bits: int) -> int:
    # Converts a two's compliment encoded value to a signed integer value
    sign_bit = bit(x, bits - 1)
    if sign_bit == 1:
        return x - (1 << bits)
    else:
        return x


def invert(x: int, bits: int) -> int:
    # Applies a binary NOT on the first N bits of x
    return x ^ mask(bits)


def mask(bits: int):
    # Returns the value 0b11...1 with N ones
    return (1 << bits) - 1


def bit(x: int, index: int):
    # Returns the Nth bit of x
    return (x >> index) & 1


def signed_bitfield(value: int, index: int, bits: int):
    # Returns the bits-length bit field of x, with an offset of index from the LSB, decoded into a signed integer from a two's compliment representation
    return sign(bitfield(value, index, bits), bits)


def bitfield(x: int, index: int, bits: int):
    # Returns the bits-length bit field of x, with an offset of index from the LSB
    return (x >> index) & mask(bits)


if __name__ == '__main__':
    main()
