inline inline_noop:
    br skip
skip:
    ret

main:
    call inline_noop
    call inline_noop
    halt
