
alias X 15
alias Y 4

seti r1 X
seti r2 Y

add r3 r1 r2    assert r3 = 19
sub r3 r1 r2    assert r3 = 11
mul r3 r1 r2    assert r3 = 60
div r3 r1 r2    assert r3 = 3
pow r3 r1 r2    assert r3 = 50625
mod r3 r1 r2    assert r3 = 3

halt
