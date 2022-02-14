
alias WIDTH 32
alias SIZE 1024

word RNG
word [32] state, next_state

alias pointer 7
alias next_pointer 8

main:
    seti @RNG 4000
    gcb G_CLEAR
seed_initial:
    # Load a random initial set of words
    seti @pointer state
    seti r1 0
seed_initial_loop:
    set @@pointer @@RNG
    and @@pointer @@pointer @@RNG  # 1/4 chance of a cell starting on
    glsd @@pointer G_32x1
    gmv r0 r1
    gcb G_DRAW_ALPHA
    addi @pointer @pointer 1
    addi r1 r1 1
    blti r1 WIDTH seed_initial_loop
    gflush

main_loop:
    seti r3 1  # x
x_loop:
    seti r4 1  # y
y_loop:

    # count neighbors
    addi r1 r3 -1  # x param
    addi r2 r4 -1  # y param
    seti r5 0  # count
    call count_at  # X.. / ... / ...
    add r5 r5 rv
    addi r1 r1 1
    call count_at  # .X. / ... / ...
    add r5 r5 rv
    addi r1 r1 1
    call count_at  # ..X / ... / ...
    add r5 r5 rv
    addi r2 r2 1
    call count_at  # ... / ..X / ...
    add r5 r5 rv
    addi r2 r2 1
    call count_at  # ... / ... / ..X
    add r5 r5 rv
    addi r1 r1 -1
    call count_at  # ... / ... / .X.
    add r5 r5 rv
    addi r1 r1 -1
    call count_at  # ... / ... / X..
    add r5 r5 rv
    addi r2 r2 -1
    call count_at  # ... / X.. / ...
    add r5 r5 rv

    # check if this cell lives or dies
    # live cell with 2 or 3 -> live cell
    # dead cell with 3 -> live cell
    # any other -> dead cell
    addi r1 r1 1  # move to center
    call count_at  # ... / .X. / ...

    beqi r5 3 cell_lives
    eqi r10 r5 2
    and r10 r10 rv
    beqi r10 1 cell_lives
cell_dies:
    call set_next_dead
    br after_set_cell
cell_lives:
    call set_next_live

after_set_cell:
    addi r4 r4 1  # y++
    blti r4 31 y_loop  # y < 31

    addi r3 r3 1  # x++
    blti r3 31 x_loop  # x < 31

    # Copy next state to state, and refresh gpu
    gcb G_CLEAR
    seti r1 0
    seti @pointer state
    seti @next_pointer next_state
copy_loop:
    set @@pointer @@next_pointer
    glsd @@pointer G_32x1
    gmv r0 r1
    gcb G_DRAW_ALPHA
    addi @pointer @pointer 1
    addi @next_pointer @next_pointer 1
    addi r1 r1 1
    blti r1 WIDTH copy_loop
    gflush

    br main_loop
    halt

count_at:
    # r1 = x, r2 = y
    # Checking a bit: bit = (number >> n) & 1U;
    addi r10 r2 state
    rs r11 @r10 r1
    andi rv r11 1
    ret

set_next_live:
    # r1 = x, r2 = y
    # Set bit: number |= 1UL << n;
    lsi r10 1 r1
    addi r11 r2 next_state
    or @r11 @r11 r10
    ret

set_next_dead:
    # r1 = x, r2 = y
    # Clear bit: number &= ~(1UL << n);
    lsi r10 1 r1
    nori r10 r10 0
    addi r11 r2 next_state
    and @r11 @r11 r10
    ret
