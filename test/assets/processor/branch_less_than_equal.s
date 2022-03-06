main:
    seti r1 1
    seti r2 2
    ble r1 r2 first
    assert r0 = 1  # Branch Not Taken
first:
    assert r1 = 1
    assert r2 = 2
    ble r2 r1 second
    halt
second:
    assert r0 = 2  # Branch Taken
