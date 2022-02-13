from enum import IntEnum
from typing import Tuple, List, Set, Optional, Union
from utils import Interval
from constants import Instructions, Registers

import enum
import utils


class ScanToken(IntEnum):
    IDENTIFIER = enum.auto()
    INSTRUCTION = enum.auto()
    REGISTER = enum.auto()
    ALIAS = enum.auto()
    ASSERT = enum.auto()
    INTEGER = enum.auto()
    WORD = enum.auto()
    SPRITE = enum.auto()
    INCLUDE = enum.auto()
    TEXTURE = enum.auto()
    SPRITE_LITERAL = enum.auto()
    STRING = enum.auto()
    AT = enum.auto()
    DOT = enum.auto()
    COLON = enum.auto()
    EQUALS = enum.auto()
    MINUS = enum.auto()
    LBRACKET = enum.auto()
    RBRACKET = enum.auto()
    COMMA = enum.auto()
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
    SPRITE = set('.#')
    IDENTIFIER = IDENTIFIER_START | NUMERIC
    INSTRUCTIONS = {i.value for i in Instructions}
    REGISTERS = {i.name.lower() for i in Registers}
    KEYWORDS = {
        'alias': ScanToken.ALIAS,
        'assert': ScanToken.ASSERT,
        'word': ScanToken.WORD,
        'sprite': ScanToken.SPRITE,
        'include': ScanToken.INCLUDE,
        'texture': ScanToken.TEXTURE
    }
    SYNTAX = {
        '@': ScanToken.AT,
        '.': ScanToken.DOT,
        ':': ScanToken.COLON,
        '=': ScanToken.EQUALS,
        '[': ScanToken.LBRACKET,
        ']': ScanToken.RBRACKET,
        ',': ScanToken.COMMA
    }
    SIGNED_INT = utils.interval_bitfield(32, True)
    UNSIGNED_INT = utils.interval_bitfield(32, False)

    Token = Union[ScanToken, ScanError, int, str]

    def __init__(self, text: str):
        self.text: str = text + '\n'  # ensure we always end with a newline
        self.pointer: int = 0
        self.output_tokens: List[Scanner.Token] = []
        self.locations: List[Tuple[int, int]] = []
        self.line_num: int = 0
        self.error: Optional[ScanError] = None

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
            self.error = e
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
                    self.err('Expected binary digit after \'0b\'')
            elif c == 'x':
                self.pointer += 1
                c = self.next()
                if c in Scanner.NUMERIC_HEX:
                    self.scan_hex_integer()
                else:
                    self.err('Expected hex digit after \'0x\'')
            elif c not in Scanner.NUMERIC:
                # This is actually a decimal '0', with no numeric characters following
                # This explicitly disallows '00' as an alternative zero
                self.push(ScanToken.INTEGER, 0)
            else:
                self.err('Undefined integer prefix: \'0%s\'' % c)
        elif c == '#':
            self.scan_comment()
        elif c == '"':
            self.scan_string()
        elif c in Scanner.SYNTAX:
            self.pointer += 1
            self.push(Scanner.SYNTAX[c])
        elif c == '`':
            self.scan_sprite_literal()
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

    def scan_string(self):
        self.pointer += 1
        c = self.next()
        acc = ''
        while c != '"' and c not in Scanner.NEWLINE:
            acc += c
            self.pointer += 1
            c = self.next()
        if c == '"':
            self.pointer += 1
            self.push(ScanToken.STRING, acc)
        else:
            self.err('Unterminated string literal')

    def scan_sprite_literal(self):
        self.pointer += 1
        c = self.next()
        lines = []
        line = ''
        while c != '`':
            if c in Scanner.NEWLINE:
                self.line_num += 1
                if line != '':
                    lines.append(line)
                    line = ''
            elif c in Scanner.SPRITE:
                line += c
            elif c in Scanner.WHITESPACE:
                pass
            else:
                self.err('Illegal token in sprite literal: \'%s\'' % c)
            self.pointer += 1
            c = self.next()

        if not lines:
            self.err('Empty sprite literal not allowed')
        if any(len(line) != len(lines[0]) for line in lines):
            self.err('Sprite literal lines must all be of the same width')
        if any(len(line) > 32 for line in lines) or len(lines) > 32:
            self.err('Sprite literal must be within [32 x 32]')

        self.push(ScanToken.SPRITE_LITERAL, '|'.join(lines))
        self.pointer += 1

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
