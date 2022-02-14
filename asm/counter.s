texture TEXTURE_DIGITS "../asm/textures/7seg_numbers.png"

sprite SPRITE_DIGITS [
    TEXTURE_DIGITS [ 0  0 3 5 ]  # 0
    TEXTURE_DIGITS [ 4  0 3 5 ]  # 1
    TEXTURE_DIGITS [ 8  0 3 5 ]  # 2
    TEXTURE_DIGITS [ 12 0 3 5 ]  # 3
    TEXTURE_DIGITS [ 16 0 3 5 ]  # 4
    TEXTURE_DIGITS [ 0  6 3 5 ]  # 5
    TEXTURE_DIGITS [ 4  6 3 5 ]  # 6
    TEXTURE_DIGITS [ 8  6 3 5 ]  # 7
    TEXTURE_DIGITS [ 12 6 3 5 ]  # 8
    TEXTURE_DIGITS [ 16 6 3 5 ]  # 9
]

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
