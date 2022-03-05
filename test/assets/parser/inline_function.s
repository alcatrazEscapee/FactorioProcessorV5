inline increment_r1:
    addi r1 r1 1
    ret

main:
    seti r1 0
    call increment_r1
    call increment_r1
    halt
