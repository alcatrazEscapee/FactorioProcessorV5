start:
    # Init
    seti r1 0
    seti r2 0
    seti r3 0
    seti r4 0

    call foo

    assert r1 = 0
    assert r2 = 2
    assert r3 = 3
    assert r4 = 0
    halt

    noop
    seti r1 1
foo:
    seti r2 2
    seti r3 3
    ret
    seti r4 4