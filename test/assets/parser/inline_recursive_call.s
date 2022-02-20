inline double_r1:
    add r1 r1 r1
    ret

inline quadruple_r1:
    call double_r1
    call double_r1
    ret

main:
    seti r1 123
    call quadruple_r1
    halt
