
alias X 0b1100
alias Y 0b1001

seti r1 X

andi  r3 r1 Y
ori   r4 r1 Y
nandi r5 r1 Y
nori  r6 r1 Y
xori  r7 r1 Y
xnori r8 r1 Y
lsi   r9 r1 Y
rsi   r10 r1 Y

lsi r11 Y r1
rsi r12 Y r1

assert r3 = 0b1000
assert r4 = 0b1101
assert r5 = -9
assert r6 = -14
assert r7 = 0b0101
assert r8 = -6
assert r9 = 6144
assert r10 = 0
assert r11 = 36864
assert r12 = 0

halt
