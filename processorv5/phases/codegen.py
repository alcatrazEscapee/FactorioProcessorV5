from typing import Tuple, List, Dict
from constants import Opcodes, GPUInstruction, GPUFunction, GPUImageDecoder
from phases.parser import Parser, ParseToken

import utils


class CodeGen:

    def __init__(self, parser: Parser):
        self.input_tokens = parser.output_tokens
        self.labels = parser.labels
        self.output_code: List[int] = []
        self.asserts: Dict[int, Tuple[int, int]] = {}
        self.sprites: List[str] = parser.sprites
        self.pointer = 0

    def gen(self):
        while not self.eof():
            t = self.next()
            if t == ParseToken.TYPE_A:
                self.pointer += 1
                self.gen_type_a()
            elif t == ParseToken.TYPE_B:
                self.pointer += 1
                self.gen_type_b()
            elif t == ParseToken.TYPE_C:
                self.pointer += 1
                self.gen_type_c()
            elif t == ParseToken.TYPE_D:
                self.pointer += 1
                self.gen_type_d()
            elif t == ParseToken.TYPE_E:
                self.pointer += 1
                self.gen_type_e()
            elif t == ParseToken.TYPE_F:
                self.pointer += 1
                self.gen_type_f()
            elif t == ParseToken.ASSERT:
                self.pointer += 1
                self.gen_assert()
            else:
                break
        if not self.next() == ParseToken.EOF:
            self.err()
        return True

    def gen_type_a(self):
        # [Opcode - 6b][Unused - 10b][Operand 1 - 16b] | [Operand 2 - 16b][Operand 3 - 16b]
        # op X Y Z -> X = 2, Y = 1, Z = 3
        opcode = self.gen_opcode()
        p1, p2, p3 = self.gen_address(), self.gen_address(), self.gen_address()
        self.output_code.append((opcode << 58) | (p2 << 32) | (p1 << 16) | (p3 << 0))

    def gen_type_b(self):
        # [Opcode - 6b][Immediate - 26b] | [Operand 2 - 16b][Operand 3 - 16b]
        opcode = self.gen_opcode()
        p1, p2, imm = self.gen_address(), self.gen_address(), self.gen_immediate26()
        self.output_code.append((opcode << 58) | (imm << 32) | (p1 << 16) | (p2 << 0))

    def gen_type_c(self):
        # [Opcode - 6b][Unused - 10b][Operand 1 - 16b] | [Branch Offset - 16b][Operand 3 - 16b]
        opcode = self.gen_opcode()
        p1, p2, offset = self.gen_address(), self.gen_address(), self.gen_branch_target()
        self.output_code.append((opcode << 58) | (p1 << 32) | (offset << 16) | (p2 << 0))

    def gen_type_d(self):
        # [Opcode - 6b][Immediate - 26b] | [Branch Offset - 16b][Operand 3 - 16b]
        opcode = self.gen_opcode()
        p1, imm, offset = self.gen_address(), self.gen_immediate26(), self.gen_branch_target()
        self.output_code.append((opcode << 58) | (imm << 32) | (offset << 16) | (p1 << 0))

    def gen_type_e(self):
        # Special
        opcode = self.gen_opcode()
        spec = Opcodes(opcode)
        if spec == Opcodes.HALT or spec == Opcodes.RET:
            self.output_code.append(opcode << 58)
        elif spec == Opcodes.CALL:
            offset = self.gen_branch_target()
            self.output_code.append((opcode << 58) | (offset << 16))
        else:
            raise NotImplementedError

    def gen_type_f(self):
        # GPU
        opcode = utils.to_bitfield(Opcodes.GPU.value, 6, 0)
        func: GPUInstruction = self.take()
        gpu_opcode = utils.to_bitfield(func.value, 3, 0)
        instruction = (opcode << 58) | (gpu_opcode << 55)
        if func == GPUInstruction.GFLUSH:
            self.output_code.append(instruction)
        elif func == GPUInstruction.GLSI:
            imm: int = self.take()
            self.output_code.append(instruction | utils.to_bitfield(imm, 16, 32))
        elif func == GPUInstruction.GLS:
            p1 = self.gen_address()
            self.output_code.append(instruction | (p1 << 32))
        elif func == GPUInstruction.GLSD:
            p1 = self.gen_address()
            f: GPUImageDecoder = self.take()
            self.output_code.append(instruction | utils.to_bitfield(f.value, 4, 51) | (p1 << 32))
        elif func == GPUInstruction.GCB or func == GPUInstruction.GCI:
            f: GPUFunction = self.take()
            self.output_code.append(instruction | utils.to_bitfield(f.value, 4, 51))
        elif func == GPUInstruction.GMV:
            x, y = self.gen_address(), self.gen_address()
            self.output_code.append(instruction | utils.to_bitfield(x, 16, 32) | utils.to_bitfield(y, 16, 0))
        elif func == GPUInstruction.GMVI:
            px, py = self.take(), self.take()
            self.output_code.append(instruction | (px << 32) | (py << 0))
        else:
            self.err()

    def gen_assert(self):
        # Interpreted assert - output the assert data to a different stream and just output a single 'assert' instruction to code
        p1, imm = self.gen_address(), self.gen_immediate32()
        self.output_code.append(Opcodes.ASSERT.value << 58)
        self.asserts[len(self.output_code) - 1] = (p1, imm)

    def gen_opcode(self) -> int:
        value: ParseToken = self.take()
        return utils.to_bitfield(value.value, 6, 0)

    def gen_address(self) -> int:
        t: ParseToken = self.take()
        if t == ParseToken.ADDRESS_CONSTANT:
            value: int = self.take()
            return utils.to_bitfield(value, 10, 6)
        elif t == ParseToken.ADDRESS_INDIRECT:
            value: int = self.take()
            offset: int = self.take()
            return utils.to_bitfield(value, 10, 6) | utils.to_signed_bitfield(offset, 5, 1) | 0b1
        else:
            self.err()

    def gen_branch_target(self) -> int:
        self.expect(ParseToken.LABEL)
        label: str = self.take()
        branch_point = self.labels[label]
        code_point = len(self.output_code)
        return utils.to_signed_bitfield(branch_point - code_point, 16, 0)

    def gen_immediate26(self) -> int:
        self.expect(ParseToken.IMMEDIATE_26)
        return utils.to_signed_bitfield(self.take(), 26, 0)

    def gen_immediate32(self) -> int:
        self.expect(ParseToken.IMMEDIATE_32)
        return self.take()

    def eof(self) -> bool:
        return self.pointer >= len(self.input_tokens)

    def err(self):
        raise AssertionError('\n'.join([
            'Code gen in inoperable state:',
            'Last     : ' + str(self.input_tokens[self.pointer - 1::-1]),
            'Next     : ' + str(self.next()),
            'Incoming : ' + str(self.input_tokens[self.pointer + 1:])
        ]))

    def expect(self, token: Parser.Token):
        t = self.take()
        if t != token:
            self.err()

    def take(self) -> Parser.Token:
        t = self.next()
        self.pointer += 1
        return t

    def next(self) -> Parser.Token:
        return self.input_tokens[self.pointer]
