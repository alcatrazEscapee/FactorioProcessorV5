
alias X 0b1100
alias Y 0b1001

seti r1 X
seti r2 Y

and  r3 r1 r2
or   r4 r1 r2
nand r5 r1 r2
nor  r6 r1 r2
xor  r7 r1 r2
xnor r8 r1 r2
ls   r9 r1 r2
rs   r10 r1 r2

assert r3 = 0b1000
assert r4 = 0b1101
assert r5 = -9
assert r6 = -14
assert r7 = 0b0101
assert r8 = -6
assert r9 = 6144
assert r10 = 0

halt
