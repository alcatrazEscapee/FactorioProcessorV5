include "./7seg_numbers.s"

word count

main:
    seti @count 0
    gcb G_CLEAR
    gflush
loop:
    # Extract digits
    modi r1 @count 10
    divi r2 @count 10
    # Graphics
    gcb G_CLEAR
    addi r3 r1 SPRITE_DIGITS
    gls r3
    gmvi 15 6
    gcb G_DRAW_ALPHA
    addi r3 r2 SPRITE_DIGITS
    gls r3
    gmvi 11 6
    gcb G_DRAW_ALPHA
    gflush
    # Increment and modulo
    addi @count @count 1
    modi @count @count 100
    # Loop
    br loop
