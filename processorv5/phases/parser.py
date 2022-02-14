from enum import IntEnum
from typing import Tuple, List, Dict, Sequence, Optional, Union, Literal, Callable, Iterable
from utils import Interval, TextureHelper
from constants import Opcodes, Instructions, Registers, GPUInstruction, GPUFunction
from phases.scanner import Scanner, ScanToken

import os
import enum
import utils
import constants
import Levenshtein


class ParseToken(IntEnum):
    ADD = Opcodes.ADD
    SUB = Opcodes.SUB
    MUL = Opcodes.MUL
    DIV = Opcodes.DIV
    POW = Opcodes.POW
    MOD = Opcodes.MOD
    AND = Opcodes.AND
    OR = Opcodes.OR
    NAND = Opcodes.NAND
    NOR = Opcodes.NOR
    XOR = Opcodes.XOR
    XNOR = Opcodes.XNOR
    LS = Opcodes.LS
    RS = Opcodes.RS
    EQ = Opcodes.EQ
    NE = Opcodes.NE
    LT = Opcodes.LT
    LE = Opcodes.LE
    ADDI = Opcodes.ADDI
    SUBIR = Opcodes.SUBIR
    MULI = Opcodes.MULI
    DIVI = Opcodes.DIVI
    DIVIR = Opcodes.DIVIR
    POWI = Opcodes.POWI
    POWIR = Opcodes.POWIR
    MODI = Opcodes.MODI
    MODIR = Opcodes.MODIR
    ANDI = Opcodes.ANDI
    ORI = Opcodes.ORI
    NANDI = Opcodes.NANDI
    NORI = Opcodes.NORI
    XORI = Opcodes.XORI
    XNORI = Opcodes.XNORI
    LSI = Opcodes.LSI
    RSI = Opcodes.RSI
    LSIR = Opcodes.LSIR
    RSIR = Opcodes.RSIR
    EQI = Opcodes.EQI
    NEI = Opcodes.NEI
    LTI = Opcodes.LTI
    GTI = Opcodes.GTI
    BEQ = Opcodes.BEQ
    BNE = Opcodes.BNE
    BLT = Opcodes.BLT
    BLE = Opcodes.BLE
    BEQI = Opcodes.BEQI
    BNEI = Opcodes.BNEI
    BLTI = Opcodes.BLTI
    BGTI = Opcodes.BGTI
    CALL = Opcodes.CALL
    RET = Opcodes.RET
    HALT = Opcodes.HALT

    # Instruction types (opcode types, not assembly instruction types)
    TYPE_A = enum.auto()  # Three operand
    TYPE_B = enum.auto()  # Two operand immediate
    TYPE_C = enum.auto()  # Two operand offset
    TYPE_D = enum.auto()  # Operand immediate offset
    TYPE_E = enum.auto()  # Special
    TYPE_F = enum.auto()  # GPU

    # Address types
    ADDRESS_CONSTANT = enum.auto()
    ADDRESS_INDIRECT = enum.auto()

    # Values
    IMMEDIATE_32 = enum.auto()  # used for non-native asserts
    IMMEDIATE_26 = enum.auto()
    IMMEDIATE_13 = enum.auto()

    LABEL = enum.auto()

    EOF = enum.auto()
    ASSERT = enum.auto()
    ERROR = enum.auto()

    # Halt error codes
    HALT_ASSERT_FAILED = enum.auto()


class ParseError(Exception):
    def __init__(self, reason: str, token_num: int, token_got: Union[ScanToken, str, int, None]):
        self.reason = reason
        self.token_num = token_num
        self.line_num: Union[str, int] = '?'
        self.line_idx: Union[str, int] = '?'
        self.line = ''

        if isinstance(token_got, ScanToken):
            token_got = token_got.name

        self.indicator = repr(token_got)
        self.has_scan_context = False

    def trace(self, scanner: Scanner):
        self.has_scan_context = True
        self.line, self.line_num, self.line_idx = scanner.context(self.token_num)
        self.indicator = '-' * (len(self.line[:self.line_idx]) - 1) + '^'

    def __str__(self):
        if self.has_scan_context:
            return '%s on line %d:\n%s\n%s' % (self.reason, self.line_num, self.line, self.indicator)
        else:
            return '%s at token %d at %s' % (self.reason, self.token_num, self.indicator)


class ParserInstruction:
    """ Assembly + Parser level understanding of an instruction """

    def parse(self, parser: 'Parser'):
        raise NotImplementedError

class CustomInstruction(ParserInstruction):

    def __init__(self, tokens: Callable[['Parser'], Tuple['Parser.Token', ...]], feed: Callable[[Tuple['Parser.Token', ...]], Tuple['Parser.Token', ...]] = None):
        self.tokens = tokens
        self.feed = feed

    def parse(self, parser: 'Parser'):
        tokens = self.tokens(parser)
        if self.feed is not None:
            tokens = self.feed(tokens)
        parser.push(*tokens)

class TypeAInstruction(ParserInstruction):
    """ Three operand instruction """

    def __init__(self, opcode: ParseToken):
        self.opcode = opcode

    def parse(self, parser: 'Parser'):
        p1, p2, p3 = parser.parse_address(), parser.parse_address(), parser.parse_address()
        parser.push(ParseToken.TYPE_A, self.opcode, *p1, *p2, *p3)

class TypeARInstruction(TypeAInstruction):
    """ Three operand pseudo instruction, with reversed parameter order """

    def parse(self, parser: 'Parser'):
        p1, p2, p3 = parser.parse_address(), parser.parse_address(), parser.parse_address()
        parser.push(ParseToken.TYPE_A, self.opcode, *p1, *p3, *p2)  # reverse order

class TypeBRInstruction(ParserInstruction):
    """ Two operand immediate instruction, with non-symmetric usage. """

    def __init__(self, arg_immediate: ParseToken, immediate_arg: ParseToken, immediate: Callable[['Parser', bool, int], int] = None):
        self.arg_immediate = arg_immediate
        self.immediate_arg = immediate_arg
        self.immediate = immediate

    def parse(self, parser: 'Parser'):
        p1 = parser.parse_address()
        p2, imm, rev = parser.parse_address_immediate26_pair()
        if self.immediate is not None:
            imm = self.immediate(parser, rev, imm)
        if rev:
            parser.push(ParseToken.TYPE_B, self.immediate_arg, *p1, *p2, ParseToken.IMMEDIATE_26, imm)
        else:
            parser.push(ParseToken.TYPE_B, self.arg_immediate, *p1, *p2, ParseToken.IMMEDIATE_26, imm)

class TypeBInstruction(TypeBRInstruction):
    """ Two operand immediate instruction, with symmetric usage """

    def __init__(self, opcode: ParseToken):
        super().__init__(opcode, opcode)

class TypeCInstruction(ParserInstruction):
    """ Two operand offset instruction, which references a label constant """

    def __init__(self, opcode: ParseToken, reverse_operand_order: bool = False):
        self.opcode = opcode
        self.reverse_operand_order = reverse_operand_order

    def parse(self, parser: 'Parser'):
        p1, p2, label = parser.parse_address(), parser.parse_address(), parser.parse_label_reference()
        if self.reverse_operand_order:
            p1, p2 = p2, p1
        parser.push(ParseToken.TYPE_C, self.opcode, *p1, *p2, ParseToken.LABEL, label)

class TypeDRInstruction(ParserInstruction):
    """ One operand offset immediate, which reference a label constant, with non-symmetric usage """

    def __init__(self, arg_immediate: ParseToken, immediate_arg: ParseToken, immediate: Callable[['Parser', bool, int], int] = None):
        self.arg_immediate = arg_immediate
        self.immediate_arg = immediate_arg
        self.immediate = immediate

    def parse(self, parser: 'Parser'):
        p1, imm, rev = parser.parse_address_immediate26_pair()
        label = parser.parse_label_reference()
        if self.immediate is not None:
            imm = self.immediate(parser, rev, imm)
        if rev:
            parser.push(ParseToken.TYPE_D, self.immediate_arg, *p1, ParseToken.IMMEDIATE_26, imm, ParseToken.LABEL, label)
        else:
            parser.push(ParseToken.TYPE_D, self.arg_immediate, *p1, ParseToken.IMMEDIATE_26, imm, ParseToken.LABEL, label)

class TypeDInstruction(TypeDRInstruction):
    """ One operand offset immediate, which references a label constant, with symmetric usage """

    def __init__(self, opcode: ParseToken):
        super().__init__(opcode, opcode)


class Parser:

    INSTRUCTIONS = {k.value: v for k, v in {
        # Type A
        Instructions.ADD: TypeAInstruction(ParseToken.ADD),
        Instructions.SUB: TypeAInstruction(ParseToken.SUB),
        Instructions.MUL: TypeAInstruction(ParseToken.MUL),
        Instructions.DIV: TypeAInstruction(ParseToken.DIV),
        Instructions.POW: TypeAInstruction(ParseToken.POW),
        Instructions.MOD: TypeAInstruction(ParseToken.MOD),
        Instructions.AND: TypeAInstruction(ParseToken.AND),
        Instructions.OR: TypeAInstruction(ParseToken.OR),
        Instructions.NAND: TypeAInstruction(ParseToken.NAND),
        Instructions.NOR: TypeAInstruction(ParseToken.NOR),
        Instructions.XOR: TypeAInstruction(ParseToken.XOR),
        Instructions.XNOR: TypeAInstruction(ParseToken.XNOR),
        Instructions.LS: TypeAInstruction(ParseToken.LS),
        Instructions.RS: TypeAInstruction(ParseToken.RS),
        Instructions.EQ: TypeAInstruction(ParseToken.EQ),
        Instructions.NE: TypeAInstruction(ParseToken.NE),
        Instructions.LT: TypeAInstruction(ParseToken.LT),
        Instructions.LE: TypeAInstruction(ParseToken.LE),
        # Type A-R
        Instructions.GT: TypeARInstruction(ParseToken.LT),
        Instructions.GE: TypeARInstruction(ParseToken.LE),
        # Type B
        Instructions.ADDI: TypeBInstruction(ParseToken.ADDI),
        Instructions.MULI: TypeBInstruction(ParseToken.MULI),
        Instructions.ANDI: TypeBInstruction(ParseToken.ANDI),
        Instructions.ORI: TypeBInstruction(ParseToken.ORI),
        Instructions.NANDI: TypeBInstruction(ParseToken.NANDI),
        Instructions.NORI: TypeBInstruction(ParseToken.NORI),
        Instructions.XORI: TypeBInstruction(ParseToken.XORI),
        Instructions.XNORI: TypeBInstruction(ParseToken.XNORI),
        Instructions.EQI: TypeBInstruction(ParseToken.EQI),
        Instructions.NEI: TypeBInstruction(ParseToken.NEI),
        # Type B-R
        Instructions.SUBI: TypeBRInstruction(ParseToken.ADDI, ParseToken.SUBIR, lambda p, rev, imm: imm if rev else p.check_interval(-imm, Parser.IMMEDIATE_SIGNED)),
        Instructions.DIVI: TypeBRInstruction(ParseToken.DIVI, ParseToken.DIVIR),
        Instructions.POWI: TypeBRInstruction(ParseToken.POWI, ParseToken.POWIR),
        Instructions.MODI: TypeBRInstruction(ParseToken.MODI, ParseToken.MODIR),
        Instructions.LSI: TypeBRInstruction(ParseToken.LSI, ParseToken.LSIR),
        Instructions.RSI: TypeBRInstruction(ParseToken.RSI, ParseToken.RSIR),
        Instructions.LTI: TypeBRInstruction(ParseToken.LTI, ParseToken.GTI),
        Instructions.LEI: TypeBRInstruction(ParseToken.LTI, ParseToken.GTI, lambda p, rev, imm: p.check_interval(imm - 1 if rev else imm + 1, Parser.IMMEDIATE_SIGNED)),
        Instructions.GTI: TypeBRInstruction(ParseToken.GTI, ParseToken.LTI),
        Instructions.GEI: TypeBRInstruction(ParseToken.GTI, ParseToken.LTI, lambda p, rev, imm: p.check_interval(imm + 1 if rev else imm - 1, Parser.IMMEDIATE_SIGNED)),
        # Type C
        Instructions.BEQ: TypeCInstruction(ParseToken.BEQ),
        Instructions.BNE: TypeCInstruction(ParseToken.BNE),
        Instructions.BLT: TypeCInstruction(ParseToken.BLT),
        Instructions.BGT: TypeCInstruction(ParseToken.BLT, True),
        Instructions.BLE: TypeCInstruction(ParseToken.BLE),
        Instructions.BGE: TypeCInstruction(ParseToken.BLE, True),
        # Type D
        Instructions.BEQI: TypeDInstruction(ParseToken.BEQI),
        Instructions.BNEI: TypeDInstruction(ParseToken.BNEI),
        # Type D-R
        Instructions.BLTI: TypeDRInstruction(ParseToken.BLTI, ParseToken.BGTI),
        Instructions.BLEI: TypeDRInstruction(ParseToken.BLTI, ParseToken.BGTI, lambda p, rev, imm: p.check_interval(imm - 1 if rev else imm + 1, Parser.IMMEDIATE_SIGNED)),
        Instructions.BGTI: TypeDRInstruction(ParseToken.BGTI, ParseToken.BLTI),
        Instructions.BGEI: TypeDRInstruction(ParseToken.BGTI, ParseToken.BLTI, lambda p, rev, imm: p.check_interval(imm + 1 if rev else imm - 1, Parser.IMMEDIATE_SIGNED)),

        # Special
        Instructions.HALT: CustomInstruction(lambda p: (ParseToken.TYPE_E, ParseToken.HALT)),

        # Custom
        Instructions.NOOP: CustomInstruction(lambda p: (ParseToken.TYPE_A, ParseToken.ADD, *Parser.R0, *Parser.R0, *Parser.R0)),
        Instructions.SET: CustomInstruction(lambda p: (ParseToken.TYPE_A, ParseToken.ADD, *p.parse_address(), *p.parse_address(), *Parser.R0)),
        Instructions.SETI: CustomInstruction(lambda p: (ParseToken.TYPE_B, ParseToken.ADDI, *p.parse_address(), *Parser.R0, ParseToken.IMMEDIATE_26, p.parse_immediate26())),
        Instructions.BR: CustomInstruction(lambda p: (ParseToken.TYPE_C, ParseToken.BEQ, *Parser.R0, *Parser.R0, ParseToken.LABEL, p.parse_label_reference())),

        # GPU
        Instructions.GFLUSH: CustomInstruction(lambda p: (ParseToken.TYPE_F, GPUInstruction.GFLUSH)),
        Instructions.GLSI: CustomInstruction(lambda p: (ParseToken.TYPE_F, GPUInstruction.GLSI, p.parse_gpu_address())),
        Instructions.GLSM: CustomInstruction(lambda p: (ParseToken.TYPE_F, GPUInstruction.GLSM, *p.parse_address())),
        #todo: glss
        Instructions.GCB: CustomInstruction(lambda p: (ParseToken.TYPE_F, GPUInstruction.GCB, p.parse_gpu_function())),
        Instructions.GCI: CustomInstruction(lambda p: (ParseToken.TYPE_F, GPUInstruction.GCI, p.parse_gpu_function())),
        Instructions.GMV: CustomInstruction(lambda p: (ParseToken.TYPE_F, GPUInstruction.GMV, *p.parse_address(), *p.parse_address())),
        Instructions.GMVI: CustomInstruction(lambda p: (ParseToken.TYPE_F, GPUInstruction.GMVI, p.parse_gpu_move(), p.parse_gpu_move()))
    }.items()}

    INSTRUCTION_TYPES = {
        ParseToken.TYPE_A, ParseToken.TYPE_B, ParseToken.TYPE_C, ParseToken.TYPE_D, ParseToken.TYPE_E, ParseToken.TYPE_F
    }

    Token = Union[ParseToken, ParseError, GPUInstruction, GPUFunction, int, str]

    ADDRESS: Interval = utils.interval_bitfield(10, False)
    OFFSET: Interval = utils.interval_bitfield(5, True)
    IMMEDIATE_SIGNED: Interval = utils.interval_bitfield(26, True)
    IMMEDIATE_UNSIGNED: Interval = utils.interval_bitfield(26, False)
    VALUE: Interval = utils.interval_bitfield(32, True)
    GPU_ADDRESS: Interval = utils.interval_bitfield(6, False)
    GPU_MOVE: Interval = utils.interval_bitfield(5, False)

    R0 = ParseToken.ADDRESS_CONSTANT, 0

    def __init__(self, tokens: List['Scanner.Token'], assert_mode: Literal['native', 'interpreted', 'none'] = 'none', file: str = None):
        self.input_tokens: List['Scanner.Token'] = tokens
        self.output_tokens: List['Parser.Token'] = []
        self.pointer: int = 0

        self.file: str = utils.unique_path(file)
        self.root: str = os.path.dirname(self.file)
        self.includes = {self.file}

        self.code_point: int = 0  # Increment at start of instruction outputs
        self.word_count: int = constants.FIRST_GENERAL_MEMORY_ADDRESS  # Increment when a word (undefined memory address) is referenced.
        self.labels: Dict[str, int] = {}  # 'foo: ' statements
        self.undefined_labels: Dict[str, ParseError] = {}  # labels that have been referenced by an instruction but not defined yet, and the error referencing their first definition
        self.aliases: Dict[str, int] = {}  # 'alias' statements
        self.sprites: List[str] = []  # sprite literals, for GPU ROM
        self.tex_helper: TextureHelper = TextureHelper(self.root, self.err)
        self.assert_mode: Literal['native', 'interpreted', 'none'] = assert_mode

        self.error: Optional[ParseError] = None

    def trace(self, file: str, scanner: Scanner):
        with open(file, 'w') as f:
            if self.labels:
                f.write('-- Label Dump --\n')
                for label, code_point in self.labels.items():
                    f.write('%s - %d\n' % (label, code_point))
            if self.aliases:
                f.write('-- Alias Dump --\n')
                for alias, memory_point in self.aliases.items():
                    f.write('%s - %d\n' % (alias, memory_point))
            if self.sprites:
                f.write('-- Sprite Dump --\n')
                for i, sprite in enumerate(self.sprites):
                    f.write('%d : %s\n' % (i, repr(sprite)))
            start = False
            for t in self.output_tokens:
                if isinstance(t, ParseToken):
                    if start:
                        f.write('\n')
                    else:
                        start = True
                    f.write(t.name)
                elif isinstance(t, ParseError):
                    t.trace(scanner)
                    f.write(' ' + str(t))
                elif isinstance(t, GPUInstruction) or isinstance(t, GPUFunction):
                    f.write(' ' + t.name)
                else:
                    f.write(' ' + repr(t))
            f.write('\n')

    def parse(self) -> bool:
        try:
            while not self.eof():
                t = self.next()
                if t == ScanToken.IDENTIFIER:
                    self.pointer += 1
                    self.parse_label()
                elif t == ScanToken.INSTRUCTION:
                    self.pointer += 1
                    self.parse_instruction()
                elif t == ScanToken.ALIAS:
                    self.pointer += 1
                    self.parse_alias()
                elif t == ScanToken.WORD:
                    self.pointer += 1
                    self.parse_word()
                elif t == ScanToken.SPRITE:
                    self.pointer += 1
                    self.parse_sprite()
                elif t == ScanToken.TEXTURE:
                    self.pointer += 1
                    self.parse_texture()
                elif t == ScanToken.INCLUDE:
                    self.pointer += 1
                    self.parse_include()
                elif t == ScanToken.ASSERT:
                    self.pointer += 1
                    self.parse_assert()
                elif t == ScanToken.EOF:
                    break
                else:
                    self.err('Unknown token: \'%s\'' % str(t))

            # Check that all labels have been defined
            for label, err in self.undefined_labels.items():
                raise err

            self.expect(ScanToken.EOF)
            self.push(ParseToken.EOF)
            return True
        except ParseError as e:
            self.push(ParseToken.ERROR, e)
            self.error = e
            return False

    def parse_label(self):
        label = self.next()
        if label in self.labels:
            self.err('Duplicate label defined: ' + repr(label))
        self.pointer += 1
        self.expect(ScanToken.COLON, 'Unknown keyword, or label missing a \':\'' + self.hint(label, Instructions.names()))
        if label in self.undefined_labels:
            del self.undefined_labels[label]
        self.labels[label] = self.code_point

    def parse_label_reference(self) -> str:
        self.expect(ScanToken.IDENTIFIER, 'Expected a label reference')
        label = self.next()
        if label not in self.labels and label not in self.undefined_labels:
            self.undefined_labels[label] = self.make_err('Label used but not defined: \'%s\'%s' % (label, self.hint(label, self.labels.keys())))
        self.pointer += 1
        return label

    def parse_alias(self):
        self.expect(ScanToken.IDENTIFIER, 'Expected identifier after \'alias\' keyword')
        alias = self.next()
        if alias in self.aliases:
            self.err('Duplicate alias: ' + repr(alias))
        self.pointer += 1
        value = self.parse_int(Parser.VALUE)
        self.aliases[alias] = value

    def parse_word(self):
        c = self.next()
        if c == ScanToken.IDENTIFIER:  # Single word
            self.parse_word_with_size(1)
        elif c == ScanToken.LBRACKET:  # Array
            self.pointer += 1
            self.expect(ScanToken.INTEGER, 'Expected array size after \'[\'')
            size = self.take()
            self.expect(ScanToken.RBRACKET, 'Missing closing \']\' in array size declaration')
            self.parse_word_with_size(size)
        else:
            self.err('Expected either identifier or array size declaration after \'word\' keyword')

    def parse_word_with_size(self, size: int):
        self.parse_single_word_with_size(size)

        # Allow commas to indicate additional same-size words
        c = self.next()
        while c == ScanToken.COMMA:
            self.pointer += 1
            self.parse_single_word_with_size(size)
            c = self.next()

    def parse_single_word_with_size(self, size: int):
        if self.word_count + size - 1 >= constants.MAIN_MEMORY_SIZE:
            self.err('Memory overflow! Tried to allocate %d bytes' % (size * 4))

        self.expect(ScanToken.IDENTIFIER, 'Expected identifier after \'word\' keyword')
        word = self.next()
        if word in self.aliases:
            self.err('Duplicate definition for: ' + repr(word))
        self.pointer += 1
        value = self.word_count
        self.word_count += size
        self.aliases[word] = value

    def parse_texture(self):
        self.expect(ScanToken.IDENTIFIER, 'Expected identifier after \'texture\' keyword')
        tex = self.next()
        if tex in self.tex_helper.textures:
            self.err('Duplicate definition for: ' + repr(tex))
        self.pointer += 1
        self.expect(ScanToken.STRING, 'Expected file name after \'texture %s\'' % tex)
        file = self.take()
        self.tex_helper.textures[tex] = file

    def parse_include(self):
        self.expect(ScanToken.STRING, 'Expected file identifier after \'include\' keyword')
        ref = self.next()
        file = utils.unique_path(os.path.join(self.root, ref))
        if file not in self.includes:  # Silently allow recursive includes
            self.includes.add(file)
            try:
                text = utils.read_file(file)
            except Exception as e:
                return self.err('%s\nReading file referenced from \'include "%s"\'' % (e, ref))

            scanner = Scanner(text)
            if not scanner.scan():
                return self.err('%s\nIn file \'%s\', referenced from \'include "%s"\'' % (scanner.error, file, ref))

            # Link sub-parser's output to this parser
            parser = Parser(scanner.output_tokens, self.assert_mode, file)
            parser.output_tokens = self.output_tokens
            parser.word_count = self.word_count
            parser.labels = self.labels
            parser.aliases = self.aliases
            parser.sprites = self.sprites
            parser.includes = self.includes
            if not parser.parse():
                parser.output_tokens.pop()  # Remove the last error token, to avoid duplicating it
                parser.output_tokens.pop()
                parser.error.trace(scanner)
                return self.err('%s\nIn file \'%s\', referenced from \'include "%s"\'' % (parser.error, file, ref))

            # Remove trailing EoF
            if parser.output_tokens[-1] != ParseToken.EOF:
                return self.err('Parser terminated too early!\nIn file \'%s\', referenced from \'include "%s"\n' % (file, ref))
            parser.output_tokens.pop()
        self.pointer += 1

    def parse_sprite(self):
        self.expect(ScanToken.IDENTIFIER, 'Expected identifier after \'sprite\' keyword')
        sprite = self.next()
        if sprite in self.aliases:
            self.err('Duplicate definition for: ' + repr(sprite))
        self.aliases[sprite] = len(self.sprites)
        self.pointer += 1

        # Accept either an array or single sprite literal
        c = self.next()
        if c == ScanToken.LBRACKET:
            self.pointer += 1
            self.parse_sprite_literal_or_reference(sprite + '[0]')
            c = self.next()
            count = 1
            while c != ScanToken.RBRACKET:
                self.parse_sprite_literal_or_reference(sprite + '[%d]' % count)
                c = self.next()
                count += 1
            self.pointer += 1
        else:
            self.parse_sprite_literal_or_reference(sprite)

    def parse_sprite_literal_or_reference(self, name: str):
        c = self.next()
        if c == ScanToken.SPRITE_LITERAL:
            self.pointer += 1
            sprite = self.take()
        elif c == ScanToken.IDENTIFIER:
            self.pointer += 1
            name = self.take()
            self.expect(ScanToken.LBRACKET, 'Expected texture parameters [x y w h] after texture name')
            self.expect(ScanToken.INTEGER, 'Expected texture parameter x')
            tex_x = self.take()
            self.expect(ScanToken.INTEGER, 'Expected texture parameter y')
            tex_y = self.take()
            self.expect(ScanToken.INTEGER, 'Expected texture parameter w')
            tex_w = self.take()
            self.expect(ScanToken.INTEGER, 'Expected texture parameter h')
            tex_h = self.take()
            self.expect(ScanToken.RBRACKET, 'Expected closing \']\' after texture parameters')
            sprite = self.tex_helper.load_sprite(name, tex_x, tex_y, tex_w, tex_h)
        else:
            self.err('Expected either sprite literal or texture to follow \'sprite\'')
            sprite = None

        if len(self.sprites) >= constants.GPU_MEMORY_SIZE:
            self.err('GPU Memory overflow, cannot allocate space for sprite \'%s\'' % name)

        self.sprites.append(sprite)

    def parse_assert(self):
        p1 = self.parse_address()
        self.expect(ScanToken.EQUALS, 'Expected \'=\' after \'assert <address>\' statement')
        value = self.parse_int(Parser.VALUE)
        if self.assert_mode == 'native':
            # assert A = #V is transpiled to native code, but this only supports 26-bit immediate values
            # bne A #V assert_label_1
            # halt ERROR_ASSERT_FAILED
            # assert_label_1:
            raise NotImplementedError
        elif self.assert_mode == 'interpreted':
            # assert A == #V is transpiled to a single 'assert' instruction, which is otherwise a noop instruction
            # This is passed onto the codegen as an 'assert'
            self.push(ParseToken.ASSERT, *p1, ParseToken.IMMEDIATE_32, value)
        elif self.assert_mode == 'none':
            # Asserts are not outputted to the next stage
            pass

    def parse_instruction(self):
        opcode = self.next()
        self.pointer += 1
        if opcode in Parser.INSTRUCTIONS:
            inst = Parser.INSTRUCTIONS[opcode]
            inst.parse(self)
        else:
            print(repr(opcode))
            print(repr(Parser.INSTRUCTIONS))
            raise NotImplementedError('Instruction: ' + opcode)

    def parse_address_immediate26_pair(self) -> Tuple[Sequence['Parser.Token'], int, bool]:
        t = self.next()
        if t == ScanToken.AT or t == ScanToken.REGISTER:
            return self.parse_address(), self.parse_immediate26(), False
        else:
            imm = self.parse_immediate26()
            address = self.parse_address()
            return address, imm, True

    def parse_address(self) -> Sequence['Parser.Token']:
        t = self.next()
        if t == ScanToken.AT:
            self.pointer += 1
            t = self.next()
            if t == ScanToken.AT:
                # Indirect (+Offset), with integer values
                # All output tokens either have an offset or offset of zero
                self.pointer += 1
                base = self.parse_address_base()
                offset = self.parse_optional_address_offset()
                return ParseToken.ADDRESS_INDIRECT, base, offset
            elif t == ScanToken.REGISTER:
                # Indirect (+Offset), with named register
                self.pointer += 1
                reg = self.take()
                offset = self.parse_optional_address_offset()
                return ParseToken.ADDRESS_INDIRECT, Registers[reg.upper()].value, offset
            else:
                # Constant
                base = self.parse_address_base()
                return ParseToken.ADDRESS_CONSTANT, base
        elif t == ScanToken.REGISTER:
            # Constant, using special register
            # No offset, as @r.i is just @r+i
            self.pointer += 1
            reg = self.take()
            return ParseToken.ADDRESS_CONSTANT, Registers[reg.upper()].value
        else:
            self.err('Address must start with indirect or a named register.')

    def parse_optional_address_offset(self) -> int:
        t = self.next()
        if t == ScanToken.DOT:
            self.pointer += 1
            return self.parse_address_offset()
        return 0

    def parse_address_base(self) -> int:
        return self.parse_literal_or_named_constant(Parser.ADDRESS)

    def parse_address_offset(self) -> int:
        return self.parse_literal_or_named_constant(Parser.OFFSET)

    def parse_gpu_address(self) -> int:
        return self.parse_literal_or_named_constant(Parser.GPU_ADDRESS)

    def parse_immediate26(self) -> int:
        return self.parse_literal_or_named_constant(Parser.IMMEDIATE_SIGNED)

    def parse_gpu_move(self) -> int:
        return self.parse_literal_or_named_constant(Parser.GPU_MOVE)

    def parse_literal_or_named_constant(self, interval: Interval) -> int:
        t = self.next()
        if t == ScanToken.IDENTIFIER:
            self.pointer += 1
            alias = self.next()
            if alias not in self.aliases:
                self.err('Undefined alias \'%s\'%s' % (alias, self.hint(alias, self.aliases.keys())))
            self.pointer += 1
            value = self.aliases[alias]

            # Identifiers can all have optional array index declarations following them
            # This is to support word and sprite arrays, when using constant indexes
            t = self.next()
            if t == ScanToken.LBRACKET:
                self.pointer += 1
                self.expect(ScanToken.INTEGER, 'Expected integer offset after \'[\'')
                value += self.take()
                self.expect(ScanToken.RBRACKET, 'Missing closing \']\' in array offset')

            return self.check_interval(value, interval)
        elif t == ScanToken.INTEGER:
            return self.parse_int(interval)
        self.err('Expected integer or named constant value')

    def parse_int(self, interval: Interval) -> int:
        self.expect(ScanToken.INTEGER, 'Expected an integer value')
        value = self.next()
        self.check_interval(value, interval)
        self.pointer += 1
        return value

    def parse_gpu_function(self) -> GPUFunction:
        self.expect(ScanToken.IDENTIFIER, 'Expected the name of a GPU function')
        func = self.next()
        try:
            func = GPUFunction[func]
            self.pointer += 1
            return func
        except KeyError:
            self.err('Not a valid GPU function: \'%s\'' % func)

    def check_interval(self, value: int, interval: Interval) -> int:
        if interval.check(value):
            return value
        self.err(interval.error(value))

    def eof(self) -> bool:
        return self.pointer >= len(self.input_tokens)

    def next(self) -> Scanner.Token:
        if self.eof():
            self.err('Unexpected EoF when parsing')
        return self.input_tokens[self.pointer]

    def take(self) -> Scanner.Token:
        t = self.next()
        self.pointer += 1
        return t

    def expect(self, expected_token: ScanToken, reason: Optional[str] = None):
        t = self.next()
        if t != expected_token:
            if reason is None:
                reason = 'Expected %s' % expected_token.name
            self.err(reason)
        self.pointer += 1

    def push(self, *tokens: 'Parser.Token'):
        for token in tokens:
            if token in Parser.INSTRUCTION_TYPES:
                self.code_point += 1
            self.output_tokens.append(token)

    def hint(self, token: str, values: Iterable[str]) -> str:
        # Find a similar token and issue a hint
        distance, value = min(((Levenshtein.distance(value, token), value) for value in values))
        if distance <= 2:
            return ' (Did you mean \'%s\'?)' % value
        return ''

    def err(self, reason: str):
        raise self.make_err(reason)

    def make_err(self, reason: str) -> ParseError:
        safe_pointer = self.pointer - 1 if self.eof() else self.pointer
        return ParseError(reason, safe_pointer, self.input_tokens[safe_pointer])
