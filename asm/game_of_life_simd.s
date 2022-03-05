# SIMD, Incredibly Over-Engineered Game of Life Implementation
# Comparison with game_of_life.s:
# Total Size: 96 -> 77 (Still < 2% Utilization)
# Average Instructions Executed / Loop: 52,764 -> 1,829 (+96% Speedup)

alias RNG_PORT 4000

word RNG

# Add buffer empty words on either side of 'state', so that reads from out of bounds rows always return zero
word zero1
word [32] state
word zero2
word [32] next_state

# Neighbors a0.. a7, Center ac
# a0 a1 a2
# a3 ac a4
# a5 a6 a7

word ac
word a0, a1, a2, a3, a4, a5, a6, a7

word [6] s0  # Intermediate stages
word [7] c0
word [5] s1
word [6] c1

word p1, p2, p4  # Final counts

word q  # Final state

word i  # Loop index
word pointer, next_pointer


inline draw_row:
    glsd @@pointer G_32x1
    gmv r0 @i
    gcb G_DRAW_ALPHA
    ret

main:
    seti @RNG RNG_PORT
    seti @zero1 0
    seti @zero2 0

    gcb G_CLEAR
seed_initial:
    # Load a random initial set of words
    seti @pointer state
    seti @i 0
initial_loop:
    # Generate state
    set @@pointer @@RNG
    and @@pointer @@pointer @@RNG  # 1/4 chance of a cell starting on

    call draw_row

    # Increment
    addi @pointer @pointer 1
    addi @i @i 1
    blti @i 32 initial_loop
    gflush


main_loop:
    seti @i 0

row_loop:
    # Initialize neighbor vectors
    addi @pointer @i state

    set @ac @@pointer
    lsi @a3 @ac 1
    rsi @a4 @ac 1

    set @a1 @@pointer.-1
    lsi @a0 @a1 1
    rsi @a2 @a1 1

    set @a6 @@pointer.1
    lsi @a5 @a6 1
    rsi @a7 @a6 1

    # Half-Adder Tree
    xor @s0[0] @a1 @a0  # L1
    and @c0[0] @a1 @a0

    xor @s0[1] @a2 @s0[0]  # L2
    and @c0[1] @a2 @s0[0]

    xor @s0[2] @a3 @s0[1]  # L3
    and @c0[2] @a3 @s0[1]

    xor @s0[3] @a4 @s0[2]  # L4
    and @c0[3] @a4 @s0[2]

    xor @s0[4] @a5 @s0[3]  # L5
    and @c0[4] @a5 @s0[3]

    xor @s0[5] @a6 @s0[4]  # L6
    and @c0[5] @a6 @s0[4]

    xor @p1    @a7 @s0[5]  # L7
    and @c0[6] @a7 @s0[5]

    xor @s1[0] @c0[1] @c0[0]  # R3
    and @c1[0] @c0[1] @c0[0]

    xor @s1[1] @c0[2] @s1[0]  # R4
    and @c1[1] @c0[2] @s1[0]

    xor @s1[2] @c0[3] @s1[1]  # R5
    and @c1[2] @c0[3] @s1[1]

    xor @s1[3] @c0[4] @s1[2]  # R6
    and @c1[3] @c0[4] @s1[2]

    xor @s1[4] @c0[5] @s1[3]  # R7
    and @c1[4] @c0[5] @s1[3]

    xor @p2    @c0[6] @s1[4]  # R8
    and @c1[5] @c0[6] @s1[4]

    # Wide OR
    or @p4 @c1[1] @c1[0]
    or @p4 @c1[2] @p4
    or @p4 @c1[3] @p4
    or @p4 @c1[4] @p4
    or @p4 @c1[5] @p4

    # Game of Life
    # ~p4 * p2 * ( p1 + ac )
    or @q @p1 @ac
    and @q @q @p2
    not @p4 @p4
    and @q @q @p4

    # Save to next_state
    addi @next_pointer @i next_state
    set @@next_pointer @q

    # Loop Increment
    addi @i @i 1
    blti @i 32 row_loop

    # Copy next_state -> state, and update the screen
    gcb G_CLEAR

    seti @i 0
copy_loop:

    # Copy
    addi @pointer @i state
    addi @next_pointer @i next_state
    set @@pointer @@next_pointer

    call draw_row

    addi @i @i 1
    blti @i 32 copy_loop

    gflush
    br main_loop
