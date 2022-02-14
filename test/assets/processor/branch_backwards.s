start:
    br end
    seti r1 1
    seti r2 2
    seti r3 3
middle:
    seti r4 4
    noop

    assert r1 = 0
    assert r2 = 0
    assert r3 = 0
    assert r4 = 4
    assert r5 = 5
    assert r6 = 0
    halt

    noop
    seti r1 1
end:
    seti r5 5
    br middle
    seti r6 6