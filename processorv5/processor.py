# This is a hardware level model of the ProcessorV5 architecture
# The purpose is to be able to simulate the processor architecture before implementing it in the target medium (Factorio combinators)
from typing import List, Tuple, Callable, NamedTuple, Optional, Any, Sequence, Dict
from enum import Enum
from constants import Opcodes, Registers, GPUInstruction, GPUFunction, GPUImageDecoder
from utils import ImageBuffer, AnyInt
from numpy import int32, uint64

import utils
import numpy
import constants
import dissasembler

numpy.seterr(all='ignore')


class IRData(NamedTuple):
    opcode: int32
    imm26: int32
    op1: int32
    op2: int32
    op3: int32
    branch: int32

    # GPU Fields
    gpu_opcode: int32
    gpu_function: int32


class OperandData(NamedTuple):
    addr: int32
    offset: int32
    indirect: int32


class Device:
    def writes(self, addr: int32) -> bool: return self.owns(addr)
    def reads(self, addr: int32) -> bool: return self.owns(addr)
    def owns(self, addr: int32) -> bool: return False
    def get(self, addr: int32) -> int32: return int32(0)
    def set(self, addr: int32, value: int32): pass

    def start(self): pass
    def tick(self): pass

class ZeroRegisterDevice(Device):

    def owns(self, addr: int32) -> bool: return addr == 0

class CounterDevice(Device):

    def __init__(self):
        self.tick_count = int32(0)

    def owns(self, addr: int32) -> bool: return addr == constants.COUNTER_PORT
    def get(self, addr: int32) -> int32: return self.tick_count

    def start(self): self.tick_count = int32(0)
    def tick(self): self.tick_count += int32(1)

class RandomDevice(Device):

    def owns(self, addr: int32) -> bool: return addr == constants.RANDOM_PORT
    def get(self, addr: int32) -> int32: return int32(numpy.random.randint(-2147483648, 2147483647, dtype=int32))


class GPU:

    def __init__(self, processor: 'Processor'):
        self.processor: 'Processor' = processor
        self.screen: ImageBuffer = ImageBuffer.empty()
        self.buffer: ImageBuffer = ImageBuffer.empty()
        self.image: ImageBuffer = ImageBuffer.empty()

    def exec(self, ir: IRData):
        if ir.gpu_opcode == GPUInstruction.GFLUSH:
            self.screen = self.buffer
            self.flush()
        elif ir.gpu_opcode == GPUInstruction.GLSI:
            self.image = self.gpu_mem_get(ir.op1)
        elif ir.gpu_opcode == GPUInstruction.GLS:
            self.image = self.gpu_mem_get(self.processor.mem_get_operand(ir.op1))
        elif ir.gpu_opcode == GPUInstruction.GLSD:
            self.image = ImageBuffer.unpack_decoder(GPUImageDecoder(ir.gpu_function), self.processor.mem_get_operand(ir.op1))
        elif ir.gpu_opcode == GPUInstruction.GCB:
            self.buffer = self.compose(GPUFunction(ir.gpu_function))
        elif ir.gpu_opcode == GPUInstruction.GCI:
            self.image = self.compose(GPUFunction(ir.gpu_function))
        elif ir.gpu_opcode == GPUInstruction.GMV:
            self.image = self.translate(self.processor.mem_get_operand(ir.op1), self.processor.mem_get_operand(ir.op3))
        elif ir.gpu_opcode == GPUInstruction.GMVI:
            self.image = self.translate(ir.op1, ir.op3)
        else:
            self.processor.throw(ProcessorErrorType.GPU_INVALID_OPCODE, ir.gpu_opcode)

    def flush(self):
        pass

    def gpu_mem_get(self, addr: int32) -> ImageBuffer:
        if 0 <= addr < constants.GPU_MEMORY_SIZE and addr < len(self.processor.sprites):
            if (sprite := self.processor.sprites[addr]) is not None:
                return sprite
            return self.processor.throw(ProcessorErrorType.GPU_UNINITIALIZED_MEMORY, addr)
        return self.processor.throw(ProcessorErrorType.GPU_INVALID_MEMORY_ADDRESS, addr)

    def compose(self, func: GPUFunction) -> ImageBuffer:
        return ImageBuffer.create(lambda x, y: func.apply_str(self.buffer[x, y], self.image[x, y]))

    def translate(self, dx: int, dy: int) -> ImageBuffer:
        return ImageBuffer.create(lambda x, y: self.image[x - dx, y - dy])


class ProcessorErrorType(Enum):
    GPU_UNINITIALIZED_MEMORY = 'Address=%d'
    GPU_INVALID_MEMORY_ADDRESS = 'Address=%d'
    GPU_INVALID_OPCODE = 'Opcode=%d'
    UNINITIALIZED_MEMORY = 'Address=%d'
    INVALID_MEMORY_ADDRESS_ON_READ = 'Address=%d'
    INVALID_MEMORY_ADDRESS_ON_WRITE = 'Address=%d'
    INVALID_OPCODE = 'Opcode=%d'
    UNINITIALIZED_INSTRUCTION = 'PC=%d'
    INVALID_INSTRUCTION_ADDRESS = 'PC=%d'
    ASSERT_FAILED = 'At assert %s = %d (got %d)'

    def create(self, *args: Any):
        return ProcessorError(self, *args)

class ProcessorError(Exception):

    def __init__(self, reason: 'ProcessorErrorType', *args: Any):
        self.reason: 'ProcessorErrorType' = reason
        self.message: str = reason.value % args if len(args) > 0 else reason.value

    def __str__(self):
        return self.reason.name.replace('_', ' ').title() + ': ' + self.message

def default_exception_handle(_, e: ProcessorError): raise e

class Processor:

    def __init__(self, instructions: Sequence[AnyInt] = (), sprites: Sequence[str] = (), exception_handle: Callable[['Processor', ProcessorError], Any] = default_exception_handle):
        self.memory: List[Optional[int32]] = [None] * constants.MAIN_MEMORY_SIZE  # N x 32b
        self.memory[0] = int32(0)  # R0
        self.instructions: List[Optional[uint64]] = [None] * constants.INSTRUCTION_MEMORY_SIZE  # N x 64b
        self.sprites: List[Optional[ImageBuffer]] = [None] * constants.GPU_MEMORY_SIZE  # N x 32x32b

        for i, inst in enumerate(instructions):
            self.instructions[i] = uint64(inst)
        for i, sprite in enumerate(sprites):
            self.sprites[i] = ImageBuffer.unpack(sprite)

        self.exception_handle = exception_handle

        self.running = False
        self.pc = int32(0)
        self.pc_next = int32(0)

        # Peripheral Devices
        self.r0 = ZeroRegisterDevice()
        self.counter = CounterDevice()
        self.rng = RandomDevice()
        self.devices: List[Device] = [self.r0, self.counter, self.rng]

        self.gpu = GPU(self)

    def throw(self, e: ProcessorErrorType, *args: Any) -> Any:
        self.exception_handle(self, e.create(*args))

    def run(self):
        self.running = True
        self.pc = int32(0)
        for device in self.devices:
            device.start()
        while self.running:
            self.tick()

    def tick(self):
        # Processor Tick
        ir = self.inst_get()
        ir_data: IRData = decode_ir(ir)
        self.pc_next = self.pc + int32(1)
        if ir_data.opcode not in INSTRUCTIONS:
            return self.throw(ProcessorErrorType.INVALID_OPCODE, ir_data.opcode)

        inst = INSTRUCTIONS[ir_data.opcode]
        inst.exec(self, ir_data)  # writes to memory
        self.pc = self.pc_next  # writes to pc

        # Device Tick
        for device in self.devices:
            device.tick()

    def branch_to(self, offset: int32):
        self.pc_next = self.pc + offset

    def call(self, offset: int32):
        self.mem_set(int32(Registers.RA), self.pc_next)
        self.pc_next = self.pc + offset

    def ret(self):
        self.pc_next = self.mem_get(int32(Registers.RA))

    def halt(self):
        self.running = False

    def do_assert(self, ir_data: IRData):
        actual, expected = self.mem_get_operand(ir_data.op3), ir_data.imm26
        if actual != expected:
            self.throw(ProcessorErrorType.ASSERT_FAILED, dissasembler.decode_address(ir_data.op3), expected, actual)
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
        if 1 <= addr < constants.MAIN_MEMORY_SIZE:
            if (value := self.memory[addr]) is not None:
                return value
            return self.throw(ProcessorErrorType.UNINITIALIZED_MEMORY, addr)

        for device in self.devices:
            if device.reads(addr):
                return device.get(addr)
        return self.throw(ProcessorErrorType.INVALID_MEMORY_ADDRESS_ON_READ, addr)

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
        if 1 <= addr < constants.MAIN_MEMORY_SIZE:
            self.memory[addr] = value
            return

        for device in self.devices:
            if device.writes(addr):
                return device.set(addr, value)

        self.throw(ProcessorErrorType.INVALID_MEMORY_ADDRESS_ON_WRITE, addr)

    def inst_get(self) -> uint64:
        """
        Perform an instruction read
        """
        if 0 <= self.pc < len(self.instructions):
            if (inst := self.instructions[self.pc]) is not None:
                return inst
            return self.throw(ProcessorErrorType.UNINITIALIZED_INSTRUCTION, self.pc)
        return self.throw(ProcessorErrorType.INVALID_INSTRUCTION_ADDRESS, self.pc)

    def memory_utilization(self) -> Tuple[int, str]: return get_utilization('M', self.memory)
    def instruction_memory_utilization(self) -> Tuple[int, str]: return get_utilization('I', self.instructions)
    def gpu_memory_utilization(self) -> Tuple[int, str]: return get_utilization('G', self.sprites)

    def debug_view(self):
        # Show an area around the non-zero memory
        memory_view = set()
        for i, m in enumerate(self.memory):
            if m != 0 and m is not None:
                memory_view |= {i - 1, i, i + 1}

        # Show a view of the assembly near the area
        decoded = dissasembler.decode(self.instructions)
        decoded_view = decoded[self.pc - 3:self.pc] + [decoded[self.pc] + ' <-- HERE'] + decoded[self.pc + 1:self.pc + 4]

        return '\n'.join([
            'PC: %d' % self.pc,
            '',
            'Disassembly:',
            *decoded_view,
            '',
            'Memory:',
            'Addr | Hex  | Dec',
            *['%04d | %s | %s' % (i, format(int(m), '08x') if m is not None else '????', '%d' % m if m is not None else '?') for i, m in enumerate(self.memory) if i in memory_view]
        ])


def decode_ir(ir: uint64) -> IRData:
    return IRData(
        int32(utils.bitfield_uint64(ir, 58, 6)),
        utils.signed_bitfield_64_to_32(ir, 32, 26),
        int32(utils.bitfield_uint64(ir, 32, 16)),
        int32(utils.bitfield_uint64(ir, 16, 16)),
        int32(utils.bitfield_uint64(ir, 0, 16)),
        utils.signed_bitfield_64_to_32(ir, 16, 16),
        int32(utils.bitfield_uint64(ir, 55, 3)),
        int32(utils.bitfield_uint64(ir, 51, 4))
    )


def decode_operand(operand: int32) -> OperandData:
    return OperandData(
        utils.bitfield_int32(operand, 6, 10),
        utils.signed_bitfield_32(operand, 1, 5),
        utils.bit_int32(operand, 0)
    )


def get_utilization(key: str, ls: Sequence[Optional[Any]]) -> Tuple[int, str]:
    count = sum(m is not None for m in ls)
    return count, '%s %.1f%%' % (key, 100 * count / len(ls))


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
        if self.comparator(model.mem_get_operand(ir.op1), model.mem_get_operand(ir.op3)):
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


def validate(*instructions: Instruction) -> Dict[int32, Instruction]:
    for i, inst in enumerate(instructions):
        assert i == inst.opcode.value, 'Validation Problem: Instruction %s has opcode %s but is at index %d' % (type(inst), repr(inst.opcode), i)
    return {i.opcode: i for i in instructions}


INSTRUCTIONS: Dict[int32, Instruction] = validate(
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
    ArithmeticImmediateInstruction(Opcodes.DIVI, lambda y, imm: y // imm),
    ArithmeticImmediateInstruction(Opcodes.DIVIR, lambda y, imm: imm // y),
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
    ArithmeticImmediateInstruction(Opcodes.LSIR, lambda y, imm: imm << y),
    ArithmeticImmediateInstruction(Opcodes.RSI, lambda y, imm: y >> imm),
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
    SpecialInstruction(Opcodes.ASSERT, lambda model, ir: model.do_assert(ir)),
    SpecialInstruction(Opcodes.GPU, lambda model, ir: model.gpu.exec(ir))
)
