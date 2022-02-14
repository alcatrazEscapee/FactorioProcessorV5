start:
    seti r1 1
    br skip
    seti r2 2
skip:
    seti r3 3
    assert r1 = 1
    assert r2 = 0
    assert r3 = 3
    halt