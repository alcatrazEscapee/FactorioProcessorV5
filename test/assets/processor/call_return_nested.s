start:
    # Init
    seti r1 0
    seti r2 0
    seti r3 0
    seti r4 0
    seti r5 0

    seti sp 1020
    call outer

    assert r1 = 1
    assert r2 = 2
    assert r3 = 0
    assert r4 = 4
    assert r5 = 0
    halt

outer:
    set @sp.0 ra
    subi sp sp 1

    seti r1 1
    call inner
    seti r2 2

    addi sp sp 1
    set ra @sp.0
    ret

    noop
    seti r3 3
inner:
    seti r4 4
    ret
    seti r5 5