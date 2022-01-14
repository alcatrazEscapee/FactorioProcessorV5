from enum import Enum


class AssemblyInstructions(Enum):
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
    BNEI = 'bnei'
    BLTI = 'blti'
    BLEI = 'blei'
    # blei X #M L -> blti X #M + 1 L
    BGTI = 'bgti'
    BGEI = 'bgei'
    # bgei X #M L -> bgei X #M - 1 L
    CALL = 'call'
    RET = 'ret'
    HALT = 'halt'

    NOOP = 'noop'  # noop -> add r0 r0 r0
    SET = 'set'  # set X Y -> add X Y r0
    SETI = 'seti'  # set X #M -> addi X r0 #M
