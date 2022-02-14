
alias X 0b1100
alias Y 0b1001

seti r1 X
seti r2 Y

and  r3 r1 r2    assert r3 = 0b1000
or   r3 r1 r2    assert r3 = 0b1101
nand r3 r1 r2    assert r3 = -9
nor  r3 r1 r2    assert r3 = -14
xor  r3 r1 r2    assert r3 = 0b0101
xnor r3 r1 r2    assert r3 = -6
ls   r3 r1 r2    assert r3 = 6144
rs   r3 r1 r2    assert r3 = 0

halt
