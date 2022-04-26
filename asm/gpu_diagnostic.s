
main:
    gci     G_FULL
    seti    r1 33
    seti    r2 33
    gmv     r1 r2
    gcb     G_DRAW
    gflush
    halt
