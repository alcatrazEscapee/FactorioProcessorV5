
alias X 15
alias Y 4

seti r1 X

addi r3 r1 Y
subi r4 r1 Y
muli r5 r1 Y
divi r6 r1 Y
powi r7 r1 Y
modi r8 r1 Y

subi r9 Y r1
divi r10 Y r1
modi r11 Y r1

assert r3 = 19
assert r4 = 11
assert r5 = 60
assert r6 = 3
assert r7 = 50625
assert r8 = 3

assert r9 = -11
assert r10 = 0
assert r11 = 4

halt
