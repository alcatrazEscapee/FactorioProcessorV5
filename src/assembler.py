# This is an Assembler from assembly code to binary level instructions for the ProcessorV5 architecture
# The purpose is to be able to write programs for the final implementation and hardware model levels

import sys
import enum
import utils
import argparse

from typing import Union, Tuple, List, Set, Optional, Sequence, Dict, Callable, Literal

from utils import Interval
from constants.opcodes import Opcodes
from constants.instructions import AssemblyInstructions
from constants.registers import Registers


def main(args: argparse.Namespace):
    input_text = read_file(args.file)
    scanner = Scanner(input_text)
    try:
        scanner.scan()
    except ScanError as e:
        print('Error during scan phase\n' + str(e))
        sys.exit(-1)


def read_command_line_args():
    parser = argparse.ArgumentParser(description='Assembler for Factorio ProcessorV5 architecture')

    parser.add_argument('file', type=str, help='The assembly file to be compiled')
    return parser.parse_args()


def read_file(file: str) -> str:
    with open(file) as f:
        return f.read()


class ScanToken(enum.IntEnum):
    IDENTIFIER = enum.auto()
    INSTRUCTION = enum.auto()
    REGISTER = enum.auto()
    ALIAS = enum.auto()
    ASSERT = enum.auto()
    INTEGER = enum.auto()
    AT = enum.auto()
    DOT = enum.auto()
    COLON = enum.auto()
    EQUALS = enum.auto()
    MINUS = enum.auto()
    EOF = enum.auto()
    ERROR = enum.auto()


class ScanError(Exception):

    def __init__(self, reason: str, line: str, line_num: int, line_idx: int):
        self.reason = reason
        self.line = line
        self.indicator = '-' * (line_idx - 1) + '^'
        self.line_num = line_num
        self.line_idx = line_idx

    def __str__(self):
        return '%s on line %d:\n%s\n%s' % (self.reason, self.line_num, self.line, self.indicator)


class Scanner:

    WHITESPACE = set('\r\t ')
    NEWLINE = set('\n')
    IDENTIFIER_START = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_')
    NUMERIC_START = set('123456789-')
    NUMERIC = set('0123456789')
    NUMERIC_BINARY = set('01')
    NUMERIC_HEX = set('0123456789abcdefABCDEF')
    IDENTIFIER = IDENTIFIER_START | NUMERIC
    INSTRUCTIONS = {i.value for i in AssemblyInstructions}
    REGISTERS = {i.name.lower() for i in Registers}
    KEYWORDS = {
        'alias': ScanToken.ALIAS,
        'assert': ScanToken.ASSERT
    }
    SYNTAX = {
        '@': ScanToken.AT,
        '.': ScanToken.DOT,
        ':': ScanToken.COLON,
        '=': ScanToken.EQUALS
    }
    SIGNED_INT = utils.interval_bitfield(32, True)
    UNSIGNED_INT = utils.interval_bitfield(32, False)

    Token = Union[ScanToken, ScanError, int, str]

    def __init__(self, text: str):
        self.text: str = text + '\n'  # ensure we always end with a new line
        self.pointer: int = 0
        self.output_tokens: List[Scanner.Token] = []
        self.locations: List[Tuple[int, int]] = []
        self.line_num: int = 0

    def trace(self, file: str):
        with open(file, 'w') as f:
            start = False
            for t in self.output_tokens:
                if isinstance(t, ScanToken):
                    if start:
                        f.write('\n')
                    else:
                        start = True
                    f.write(t.name)
                elif isinstance(t, ScanError):
                    f.write(' ' + str(t))
                else:
                    f.write(' ' + repr(t))
            f.write('\n')

    def scan(self) -> bool:
        try:
            while not self.eof():
                self.scan_token()
            self.push(ScanToken.EOF)
            return True
        except ScanError as e:
            self.push(ScanToken.ERROR, e)
            return False

    def scan_token(self):
        c = self.next()
        if c in Scanner.WHITESPACE:
            self.pointer += 1
        elif c in Scanner.NEWLINE:
            self.pointer += 1
            self.line_num += 1
        elif c in Scanner.IDENTIFIER_START:
            self.scan_identifier()
        elif c in Scanner.NUMERIC_START:
            self.scan_signed_integer()
        elif c == '0':
            self.pointer += 1
            c = self.next()
            if c == 'b':
                self.pointer += 1
                c = self.next()
                if c in Scanner.NUMERIC_BINARY:
                    self.scan_binary_integer()
                else:
                    self.err('Expected binary integer after 0b')
            elif c == 'x':
                self.pointer += 1
                c = self.next()
                if c in Scanner.NUMERIC_HEX:
                    self.scan_hex_integer()
                else:
                    self.err('Expected hex integer after 0x')
            elif c not in Scanner.NUMERIC:
                # This is actually a decimal '0', with no numeric characters following
                # This explicitly disallows '00' as an alternative zero
                self.push(ScanToken.INTEGER, 0)
            else:
                self.err('Undefined integer prefix: 0%s' % c)
        elif c == '#':
            self.scan_comment()
        elif c in Scanner.SYNTAX:
            self.pointer += 1
            self.push(Scanner.SYNTAX[c])
        else:
            self.pointer += 1
            self.err('Unknown token: \'%s\'' % str(c))

    def scan_identifier(self):
        identifier = self.next()
        self.pointer += 1
        c = self.next()

        while c in Scanner.IDENTIFIER:
            identifier += c
            self.pointer += 1
            c = self.next()

        # Screener
        if identifier in Scanner.INSTRUCTIONS:
            self.push(ScanToken.INSTRUCTION, identifier)
        elif identifier in Scanner.REGISTERS:
            self.push(ScanToken.REGISTER, identifier)
        elif identifier in Scanner.KEYWORDS:
            self.push(Scanner.KEYWORDS[identifier])
        else:
            self.push(ScanToken.IDENTIFIER, identifier)

    def scan_signed_integer(self):
        value = int(self.scan_numeric(Scanner.NUMERIC))
        self.push(ScanToken.INTEGER, self.check_interval(value, Scanner.SIGNED_INT))

    def scan_binary_integer(self):
        value = int(self.scan_numeric(Scanner.NUMERIC_BINARY), base=2)
        self.push(ScanToken.INTEGER, self.check_interval(value, Scanner.UNSIGNED_INT))

    def scan_hex_integer(self):
        value = int(self.scan_numeric(Scanner.NUMERIC_HEX), base=16)
        self.push(ScanToken.INTEGER, self.check_interval(value, Scanner.UNSIGNED_INT))

    def scan_numeric(self, chars: Set[str]) -> str:
        acc = self.next()  # Assume the first token is of the given chars
        self.pointer += 1
        c = self.next()
        while c in chars:
            acc += c
            self.pointer += 1
            c = self.next()
        # Next token must be non-numeric, otherwise we allow sequences like 0b123 to be 0b1 23
        if c in Scanner.NUMERIC:
            self.err('Non-numeric character must follow integer: %s' % c)
        return acc

    def scan_comment(self):
        self.pointer += 1
        c = self.next()
        while c not in Scanner.NEWLINE:
            self.pointer += 1
            c = self.next()

    def check_interval(self, value: int, interval: Interval) -> int:
        if interval.check(value):
            return value
        self.err(interval.error(value))

    def eof(self):
        return self.pointer >= len(self.text)

    def next(self):
        return self.text[self.pointer]

    def push(self, *tokens: 'Scanner.Token'):
        for token in tokens:
            self.output_tokens.append(token)
            self.locations.append((self.line_num, self.pointer - 1))

    def context(self, index: int) -> Tuple[str, int, int]:
        line_num, pointer = self.locations[index]
        lines = self.text.split('\n')
        line_idx = 1 + pointer - sum(1 + len(s) for s in lines[:line_num])
        return lines[line_num], 1 + line_num, line_idx

    def err(self, reason: str):
        lines = self.text.split('\n')
        line_idx = 1 + self.pointer - sum(1 + len(s) for s in lines[:self.line_num])
        raise ScanError(reason, lines[self.line_num], 1 + self.line_num, line_idx)


class ParseToken(enum.IntEnum):
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

    def __init__(self, tokens: Callable[['Parser'], Tuple[ParseToken, ...]], feed: Callable[[Tuple[ParseToken, ...]], Tuple[ParseToken]] = None):
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

class TypeBInstruction(ParserInstruction):
    """ Two operand immediate instruction, with symmetric usage """

    def __init__(self, opcode: ParseToken):
        self.opcode = opcode

    def parse(self, parser: 'Parser'):
        p1 = parser.parse_address()
        p2, imm, _ = parser.parse_address_immediate26_pair()
        parser.push(ParseToken.TYPE_B, self.opcode, *p1, *p2, ParseToken.IMMEDIATE_26, imm)

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

class TypeDInstruction(ParserInstruction):
    """ One operand offset immediate, which references a label constant, with symmetric usage """

    def __init__(self, opcode: ParseToken):
        self.opcode = opcode

    def parse(self, parser: 'Parser'):
        p1, imm, _ = parser.parse_address_immediate26_pair()
        label = parser.parse_label_reference()
        parser.push(ParseToken.TYPE_D, self.opcode, *p1, ParseToken.IMMEDIATE_26, imm, ParseToken.LABEL, label)

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


class Parser:

    INSTRUCTIONS = {k.value: v for k, v in {
        # Type A
        AssemblyInstructions.ADD: TypeAInstruction(ParseToken.ADD),
        AssemblyInstructions.SUB: TypeAInstruction(ParseToken.SUB),
        AssemblyInstructions.MUL: TypeAInstruction(ParseToken.MUL),
        AssemblyInstructions.DIV: TypeAInstruction(ParseToken.DIV),
        AssemblyInstructions.POW: TypeAInstruction(ParseToken.POW),
        AssemblyInstructions.MOD: TypeAInstruction(ParseToken.MOD),
        AssemblyInstructions.AND: TypeAInstruction(ParseToken.AND),
        AssemblyInstructions.OR: TypeAInstruction(ParseToken.OR),
        AssemblyInstructions.NAND: TypeAInstruction(ParseToken.NAND),
        AssemblyInstructions.NOR: TypeAInstruction(ParseToken.NOR),
        AssemblyInstructions.XOR: TypeAInstruction(ParseToken.XOR),
        AssemblyInstructions.XNOR: TypeAInstruction(ParseToken.XNOR),
        AssemblyInstructions.LS: TypeAInstruction(ParseToken.LS),
        AssemblyInstructions.RS: TypeAInstruction(ParseToken.RS),
        AssemblyInstructions.EQ: TypeAInstruction(ParseToken.EQ),
        AssemblyInstructions.NE: TypeAInstruction(ParseToken.NE),
        AssemblyInstructions.LT: TypeAInstruction(ParseToken.LT),
        AssemblyInstructions.LE: TypeAInstruction(ParseToken.LE),
        # Type A-R
        AssemblyInstructions.GT: TypeARInstruction(ParseToken.LT),
        AssemblyInstructions.GE: TypeARInstruction(ParseToken.LE),
        # Type B
        AssemblyInstructions.ADDI: TypeBInstruction(ParseToken.ADDI),
        AssemblyInstructions.MULI: TypeBInstruction(ParseToken.MULI),
        AssemblyInstructions.ANDI: TypeBInstruction(ParseToken.ANDI),
        AssemblyInstructions.ORI: TypeBInstruction(ParseToken.ORI),
        AssemblyInstructions.NANDI: TypeBInstruction(ParseToken.NANDI),
        AssemblyInstructions.NORI: TypeBInstruction(ParseToken.NORI),
        AssemblyInstructions.XORI: TypeBInstruction(ParseToken.XORI),
        AssemblyInstructions.XNORI: TypeBInstruction(ParseToken.XNORI),
        AssemblyInstructions.EQI: TypeBInstruction(ParseToken.EQI),
        AssemblyInstructions.NEI: TypeBInstruction(ParseToken.NEI),
        # Type B-R
        AssemblyInstructions.SUBI: TypeBRInstruction(ParseToken.ADDI, ParseToken.SUBIR, lambda p, rev, imm: imm if rev else p.check_interval(-imm, Parser.IMMEDIATE_SIGNED)),
        AssemblyInstructions.DIVI: TypeBRInstruction(ParseToken.DIVI, ParseToken.DIVIR),
        AssemblyInstructions.POWI: TypeBRInstruction(ParseToken.POWI, ParseToken.POWIR),
        AssemblyInstructions.MODI: TypeBRInstruction(ParseToken.MODI, ParseToken.MODIR),
        AssemblyInstructions.LSI: TypeBRInstruction(ParseToken.LSI, ParseToken.LSIR),
        AssemblyInstructions.RSI: TypeBRInstruction(ParseToken.RSI, ParseToken.RSIR),
        AssemblyInstructions.LTI: TypeBRInstruction(ParseToken.LTI, ParseToken.GTI),
        AssemblyInstructions.LEI: TypeBRInstruction(ParseToken.LTI, ParseToken.GTI, lambda p, rev, imm: p.check_interval(imm - 1 if rev else imm + 1, Parser.IMMEDIATE_SIGNED)),
        AssemblyInstructions.GTI: TypeBRInstruction(ParseToken.GTI, ParseToken.LTI),
        AssemblyInstructions.GEI: TypeBRInstruction(ParseToken.GTI, ParseToken.LTI, lambda p, rev, imm: p.check_interval(imm + 1 if rev else imm - 1, Parser.IMMEDIATE_SIGNED)),
        # Type C
        AssemblyInstructions.BEQ: TypeCInstruction(ParseToken.BEQ),
        AssemblyInstructions.BNE: TypeCInstruction(ParseToken.BNE),
        AssemblyInstructions.BLT: TypeCInstruction(ParseToken.BLT),
        AssemblyInstructions.BGT: TypeCInstruction(ParseToken.BLT, True),
        AssemblyInstructions.BLE: TypeCInstruction(ParseToken.BLE),
        AssemblyInstructions.BGE: TypeCInstruction(ParseToken.BLE, True),
        # Type D
        AssemblyInstructions.BEQI: TypeDInstruction(ParseToken.BEQI),
        AssemblyInstructions.BNEI: TypeDInstruction(ParseToken.BNEI),
        # Type D-R
        AssemblyInstructions.BLTI: TypeDRInstruction(ParseToken.BLTI, ParseToken.BGTI),
        AssemblyInstructions.BLEI: TypeDRInstruction(ParseToken.BLTI, ParseToken.BGTI, lambda p, rev, imm: p.check_interval(imm - 1 if rev else imm + 1, Parser.IMMEDIATE_SIGNED)),
        AssemblyInstructions.BGTI: TypeDRInstruction(ParseToken.BGTI, ParseToken.BLTI),
        AssemblyInstructions.BGEI: TypeDRInstruction(ParseToken.BGTI, ParseToken.BLTI, lambda p, rev, imm: p.check_interval(imm + 1 if rev else imm - 1, Parser.IMMEDIATE_SIGNED)),

        # Special
        AssemblyInstructions.HALT: CustomInstruction(lambda p: (ParseToken.TYPE_E, ParseToken.HALT)),

        # Custom
        AssemblyInstructions.NOOP: CustomInstruction(lambda p: (ParseToken.TYPE_A, ParseToken.ADD, *Parser.R0, *Parser.R0, *Parser.R0)),
        AssemblyInstructions.SET: CustomInstruction(lambda p: (ParseToken.TYPE_A, ParseToken.ADD, *p.parse_address(), *p.parse_address(), *Parser.R0)),
        AssemblyInstructions.SETI: CustomInstruction(lambda p: (ParseToken.TYPE_B, ParseToken.ADDI, *p.parse_address(), *Parser.R0, ParseToken.IMMEDIATE_26, p.parse_immediate26()))

    }.items()}

    INSTRUCTION_TYPES = {
        ParseToken.TYPE_A, ParseToken.TYPE_B, ParseToken.TYPE_C, ParseToken.TYPE_D, ParseToken.TYPE_E
    }

    Token = Union[ParseToken, ParseError, int, str]

    ADDRESS: Interval = utils.interval_bitfield(10, False)
    OFFSET: Interval = utils.interval_bitfield(5, True)
    IMMEDIATE_SIGNED: Interval = utils.interval_bitfield(26, True)
    IMMEDIATE_UNSIGNED: Interval = utils.interval_bitfield(26, False)
    VALUE: Interval = utils.interval_bitfield(32, True)

    R0 = ParseToken.ADDRESS_CONSTANT, 0

    def __init__(self, tokens: List['Scanner.Token'], assert_mode: Literal['native', 'interpreted', 'none'] = 'none'):
        self.input_tokens: List['Scanner.Token'] = tokens
        self.output_tokens: List['Parser.Token'] = []
        self.pointer: int = 0

        self.code_point: int = 0  # Increment at start of instruction outputs
        self.labels: Dict[str, int] = {}  # 'foo: ' statements
        self.undefined_labels: Dict[str, ParseError] = {}  # labels that have been referenced by an instruction but not defined yet, and the error referencing their first definition
        self.aliases: Dict[str, int] = {}  # 'alias' statements
        self.assert_mode: Literal['native', 'interpreted', 'none'] = assert_mode

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
            return False

    def parse_label(self):
        label = self.next()
        if label in self.labels:
            self.err('Duplicate label defined: ' + repr(label))
        self.pointer += 1
        self.expect(ScanToken.COLON, 'Expected \':\' after label identifier')
        if label in self.undefined_labels:
            del self.undefined_labels[label]
        self.labels[label] = self.code_point

    def parse_label_reference(self):
        self.expect(ScanToken.IDENTIFIER)
        label = self.next()
        if label not in self.labels and label not in self.undefined_labels:
            self.undefined_labels[label] = self.make_err('Label used but not defined: \'%s\'' % label)
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

    def parse_immediate26(self) -> int:
        return self.parse_literal_or_named_constant(Parser.IMMEDIATE_SIGNED)

    def parse_literal_or_named_constant(self, interval: Interval) -> int:
        t = self.next()
        if t == ScanToken.IDENTIFIER:
            self.pointer += 1
            alias = self.next()
            if alias not in self.aliases:
                self.err('Undefined alias \'%s\'' % alias)
            self.pointer += 1
            return self.check_interval(self.aliases[alias], interval)
        elif t == ScanToken.INTEGER:
            return self.parse_int(interval)
        self.err('Expected integer or named constant value')

    def parse_int(self, interval: Interval) -> int:
        self.expect(ScanToken.INTEGER, 'Expected an integer value')
        value = self.next()
        self.check_interval(value, interval)
        self.pointer += 1
        return value

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

    def err(self, reason: str):
        raise self.make_err(reason)

    def make_err(self, reason: str) -> ParseError:
        safe_pointer = self.pointer - 1 if self.eof() else self.pointer
        return ParseError(reason, safe_pointer, self.input_tokens[safe_pointer])


class CodeGen:

    def __init__(self, tokens: List[Parser.Token]):
        self.input_tokens = tokens
        self.output_code: List[int] = []
        self.asserts: Dict[int, Tuple[int, int]] = {}
        self.pointer = 0

    def trace(self, file: str):
        with open(file, 'w') as f:
            for i, code in enumerate(self.output_code):
                f.write('%04d | %s %s\n' % (i, format(code >> 32, '032b'), format(code & utils.mask(32), '032b')))

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
                raise NotImplementedError
            elif t == ParseToken.TYPE_D:
                raise NotImplementedError
            elif t == ParseToken.TYPE_E:
                raise NotImplementedError
            elif t == ParseToken.ASSERT:
                self.gen_assert()
            else:
                break
        if not self.next() == ParseToken.EOF:
            self.err()
        return True

    def gen_type_a(self):
        # [Opcode - 6b][Unused - 10b][Operand 1 - 16b] | [Operand 2 - 16b][Operand 3 - 16b]
        opcode = self.gen_opcode()
        p1, p2, p3 = self.gen_address(), self.gen_address(), self.gen_address()
        self.output_code.append((opcode << 58) | (p1 << 32) | (p2 << 16) | (p3 << 0))

    def gen_type_b(self):
        # [Opcode - 6b][Immediate - 26b] | [Operand 2 - 16b][Operand 3 - 16b]
        opcode = self.gen_opcode()
        p1, p2, imm = self.gen_address(), self.gen_address(), self.gen_immediate26()
        self.output_code.append((opcode << 58) | (imm << 32) | (p1 << 16) | (p2 << 0))

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

    def gen_immediate26(self) -> int:
        t: ParseToken = self.take()
        if t == ParseToken.IMMEDIATE_26:
            value: int = self.take()
            return utils.to_signed_bitfield(value, 26, 0)
        else:
            self.err()

    def gen_immediate32(self) -> int:
        t: ParseToken = self.take()
        if t == ParseToken.IMMEDIATE_32:
            value: int = self.take()
            return value
        else:
            self.err()

    def eof(self) -> bool:
        return self.pointer >= len(self.input_tokens)

    def err(self):
        raise AssertionError('Code gen in inoperable state. At: ' + str(self.input_tokens[self.pointer:]))

    def take(self) -> Parser.Token:
        t = self.next()
        self.pointer += 1
        return t

    def next(self) -> Scanner.Token:
        return self.input_tokens[self.pointer]


if __name__ == '__main__':
    main(read_command_line_args())
