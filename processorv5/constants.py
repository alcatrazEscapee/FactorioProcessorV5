from enum import Enum, IntEnum


GPU_MEMORY_SIZE = 64
MAIN_MEMORY_SIZE = 1024
INSTRUCTION_MEMORY_SIZE = 7680

FIRST_GENERAL_MEMORY_ADDRESS = 20

CONTROL_PORT = 2000
CONTROL_PORT_WIDTH = 5

CONTROL_PORT_X = 2000
CONTROL_PORT_UP = 2001
CONTROL_PORT_DOWN = 2002
CONTROL_PORT_LEFT = 2003
CONTROL_PORT_RIGHT = 2004

COUNTER_PORT = 3000

RANDOM_PORT = 4000

SCREEN_WIDTH = 32
SCREEN_HEIGHT = 32

STACK_POINTER_START = 1020


class Instructions(Enum):
    """
    Assembly level instructions, identified by their asm name
    Comments reference how assembly instructions transpile to their possible architecture level instructions
    """

    @staticmethod
    def names():
        return [v.value for v in Instructions]

    ADD = 'add'
    SUB = 'sub'
    MUL = 'mul'
    DIV = 'div'
    POW = 'pow'
    MOD = 'mod'
    AND = 'and'
    OR = 'or'
    NAND = 'nand'
    NOR = 'nor'
    XOR = 'xor'
    XNOR = 'xnor'
    LS = 'ls'
    RS = 'rs'
    EQ = 'eq'
    NE = 'ne'
    LT = 'lt'
    LE = 'le'
    GT = 'gt'
    # gt X Y L -> lt Y X L
    GE = 'ge'
    # ge X Y L -> le Y X L
    ADDI = 'addi'
    SUBI = 'subi'
    # subi X Y #M -> addi X Y -#M
    # subi X #M Y -> subir X Y #M
    MULI = 'muli'
    DIVI = 'divi'
    # divi X #M Y -> divir X Y #M
    POWI = 'powi'
    # powi X #M Y -> powir X Y #M
    MODI = 'modi'
    # modi X #M Y -> modir X Y #M
    ANDI = 'andi'
    ORI = 'ori'
    NANDI = 'nandi'
    NORI = 'nori'
    XORI = 'xori'
    XNORI = 'xnori'
    LSI = 'lsi'
    # lsi X #M Y -> lsir X Y #M
    RSI = 'rsi'
    # rsi X #M Y -> rsir X Y #M
    EQI = 'eqi'
    NEI = 'nei'
    LTI = 'lti'
    # lti X #M Y -> gti X Y #M
    LEI = 'lei'
    # lei X Y #M -> lti X Y #M + 1
    # lei X #M Y -> gti X Y #M - 1
    GTI = 'gti'
    # gti X #M Y -> lti X Y #M
    GEI = 'gei'
    # gei X Y #M -> gti X Y #M - 1
    # gei X #M Y -> lti X Y #M + 1
    BEQ = 'beq'
    BNE = 'bne'
    BLT = 'blt'
    BGT = 'bgt'
    # bgt X Y L -> blt Y X L
    BLE = 'ble'
    BGE = 'bge'
    # bge X Y L -> ble Y X L
    BEQI = 'beqi'
    # beqi #M X L -> beqi X #M L
    BNEI = 'bnei'
    # bnei #M X L -> bnei X #M L
    BLTI = 'blti'
    # blti #M X L -> bgti X #M L
    BLEI = 'blei'
    # blei X #M L -> blti X #M + 1 L
    # blei #M X L -> bgti X #M - 1 L
    BGTI = 'bgti'
    # bgti #M X L -> blti X #M L
    BGEI = 'bgei'
    # bgei X #M L -> bgti X #M - 1 L
    # bgei #M X L -> blti X #M + 1 L
    CALL = 'call'
    RET = 'ret'
    HALT = 'halt'

    NOOP = 'noop'  # noop -> add r0 r0 r0
    SET = 'set'  # set X Y -> add X Y r0
    SETI = 'seti'  # set X #M -> addi X r0 #M
    BR = 'br'  # br L -> beq r0 r0 L
    NOT = 'not'  # not X Y -> nor X Y r0

    GFLUSH = 'gflush'
    GLSI = 'glsi'
    GLS = 'gls'
    GLSD = 'glsd'
    GCB = 'gcb'
    GCI = 'gci'
    GMV = 'gmv'
    GMVI = 'gmvi'


class Opcodes(IntEnum):
    """ Architecture level instruction opcodes """

    # Type A
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    POW = 4
    MOD = 5
    AND = 6
    OR = 7
    NAND = 8
    NOR = 9
    XOR = 10
    XNOR = 11
    LS = 12
    RS = 13
    EQ = 14
    NE = 15
    LT = 16
    LE = 17
    # Type B
    ADDI = 18
    SUBIR = 19
    MULI = 20
    DIVI = 21
    DIVIR = 22
    POWI = 23
    POWIR = 24
    MODI = 25
    MODIR = 26
    ANDI = 27
    ORI = 28
    NANDI = 29
    NORI = 30
    XORI = 31
    XNORI = 32
    LSI = 33
    LSIR = 34
    RSI = 35
    RSIR = 36
    EQI = 37
    NEI = 38
    LTI = 39
    GTI = 40
    # Type C
    BEQ = 41
    BNE = 42
    BLT = 43
    BLE = 44
    # Type D
    BEQI = 45
    BNEI = 46
    BLTI = 47
    BGTI = 48
    # Special (Type E)
    CALL = 49
    RET = 50
    HALT = 51
    ASSERT = 52
    GPU = 53
    PRINT = 54


class Registers(IntEnum):
    """ Named memory locations (registers) """
    SP = 1023
    RA = 1022
    RV = 1021
    R0 = 0  # Non-writable (always zero)
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6
    R7 = 7
    R8 = 8
    R9 = 9
    R10 = 10
    R11 = 11
    R12 = 12
    R13 = 13
    R14 = 14
    R15 = 15
    R16 = 16


class GPUInstruction(IntEnum):
    GFLUSH = 0
    GLSI = 1
    GLS = 2
    GLSD = 3
    GCB = 4
    GCI = 5
    GMV = 6
    GMVI = 7


class GPUFunction(IntEnum):
    G_CLEAR = 0
    G_NOR = 1
    G_ERASE = 2
    G_DRAW_NEGATIVE = 3
    G_HIGHLIGHT = 4
    G_NEGATIVE = 5
    G_TOGGLE = 6
    G_NAND = 7
    G_ERASE_NEGATIVE = 8
    G_TOGGLE_NEGATIVE = 9
    G_NOOP = 10
    G_DRAW_ALPHA_NEGATIVE = 11
    G_DRAW = 12
    G_HIGHLIGHT_NEGATIVE = 13
    G_DRAW_ALPHA = 14
    G_FULL = 15

    def apply_str(self, lhs: str, rhs: str) -> str:
        return '#' if self.apply(lhs == '#', rhs == '#') else '.'

    def apply(self, lhs: bool, rhs: bool) -> bool:
        return ((self.value >> ((rhs << 1) | lhs)) & 1) != 0


class GPUImageDecoder(IntEnum):
    """ Width x Height """
    G_32x1 = 0
    G_16x2 = 1
    G_8x4 = 2
    G_4x8 = 3
    G_2x16 = 4
    G_1x32 = 5


class GPUBufferCode(IntEnum):
    GPU_ROM_OUT = 0
    IMAGE_DECODER_OUT = 1
    TRANSLATION_MATRIX_OUT = 2
    COMPOSER_OUT = 3


class GPUInputCode(IntEnum):
    IMMEDIATE = 0
    MEMORY = 1


class ALUCode(IntEnum):
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    POW = 4
    MOD = 5
    AND = 6
    OR = 7
    XOR = 8
    LS = 9
    RS = 10
    NAND = 11
    NOR = 12
    XNOR = 13
    EQ = 14
    NE = 15
    LT = 16
    GT = 17
    LE = 18
    GE = 19


class ALUInputCode(IntEnum):
    A = 0
    B = 1
    IMMEDIATE = 2


class PCInputCode(IntEnum):
    INCREMENT = 0
    RA = 1
    OFFSET = 2

class BranchCode(IntEnum):
    NONE = 0
    UNCONDITIONAL = 1
    CONDITIONAL = 2
