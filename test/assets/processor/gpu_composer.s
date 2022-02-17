texture TEXTURE_BACKGROUND "../textures/background.png"

sprite BACKGROUND TEXTURE_BACKGROUND [ 0 0 32 32 ]
sprite SQUARE `
####
####
####
####
`


main:
    call reset
    gflush  # tests G_DRAW

    gcb G_NOR
    gflush

    call reset
    gcb G_ERASE
    gflush

    call reset
    gcb G_DRAW_NEGATIVE
    gflush

    call reset
    gcb G_HIGHLIGHT
    gflush

    call reset
    gcb G_NEGATIVE
    gflush

    call reset
    gcb G_TOGGLE
    gflush

    call reset
    gcb G_NAND
    gflush

    call reset
    gcb G_ERASE_NEGATIVE
    gflush

    call reset
    gcb G_TOGGLE_NEGATIVE
    gflush

    call reset
    gcb G_NOOP
    gflush

    call reset
    gcb G_DRAW_ALPHA_NEGATIVE
    gflush

    call reset
    gcb G_HIGHLIGHT_NEGATIVE
    gflush

    call reset
    gcb G_DRAW_ALPHA
    gflush


    halt

reset:
    # Half On / Off
    glsi BACKGROUND
    gcb G_DRAW
    gflush

    # Center Square
    glsi SQUARE
    gmvi 14 14

    ret