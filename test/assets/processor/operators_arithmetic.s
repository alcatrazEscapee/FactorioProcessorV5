
alias X 15
alias Y 4

seti r1 X
seti r2 Y

add r3 r1 r2
sub r4 r1 r2
mul r5 r1 r2
div r6 r1 r2
pow r7 r1 r2
mod r8 r1 r2

assert r3 = 19
assert r4 = 11
assert r5 = 60
assert r6 = 3
assert r7 = 50625
assert r8 = 3

halt
