inline increment_r1:
    addi rX rY rZ
    ret

main:
    seti r1 0
    call increment_r1
    call increment_r1
    halt
