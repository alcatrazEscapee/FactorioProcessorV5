from enum import IntEnum


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
