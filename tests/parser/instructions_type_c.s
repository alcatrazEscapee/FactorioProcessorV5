A:
    beq r1 r2 B
    bne r1 r2 C
B:
    blt r3 r5 A
    bgt r3 r5 C
C:
    ble r4 r6 A
    bge r4 r6 C