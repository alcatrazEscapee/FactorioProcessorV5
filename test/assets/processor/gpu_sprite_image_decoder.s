sprite SPRITE_32x1
`.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#`

sprite SPRITE_16x2 `
.#.#.#.#.#.#.#.#
.#.#.#.#.#.#.#.#
`

sprite SPRITE_8x4 `
.#.#.#.#
.#.#.#.#
.#.#.#.#
.#.#.#.#
`

sprite SPRITE_4x8 `
.#.#|.#.#
.#.#|.#.#
.#.#|.#.#
.#.#|.#.#
`

sprite SPRITE_2x16 `
.#|.#|.#|.#
.#|.#|.#|.#
.#|.#|.#|.#
.#|.#|.#|.#
`

sprite SPRITE_1x32 `
.|#|.|#|.|#|.|#
.|#|.|#|.|#|.|#
.|#|.|#|.|#|.|#
.|#|.|#|.|#|.|#
`

main:
    # 32-bit immediate - todo: optimize this?
    seti r5 0xAAAA
    lsi r5 r5 16
    ori r5 r5 0xAAAA

    # Full
    gcb G_FULL
    gflush

    # Clear
    gcb G_CLEAR
    gflush

    # 32x1
    glsi SPRITE_32x1
    gcb G_DRAW
    gflush

    glsd r5 G_32x1
    gmvi 0 31
    gcb G_DRAW_ALPHA
    gflush

    # 16x2
    glsi SPRITE_16x2
    gcb G_DRAW
    gflush

    glsd r5 G_16x2
    gmvi 16 30
    gcb G_DRAW_ALPHA
    gflush

    # 8x4
    glsi SPRITE_8x4
    gcb G_DRAW
    gflush

    glsd r5 G_8x4
    gmvi 24 28
    gcb G_DRAW_ALPHA
    gflush

    # 4x8
    glsi SPRITE_4x8
    gcb G_DRAW
    gflush

    glsd r5 G_4x8
    gmvi 28 24
    gcb G_DRAW_ALPHA
    gflush

    # 2x16
    glsi SPRITE_2x16
    gcb G_DRAW
    gflush

    glsd r5 G_2x16
    gmvi 30 16
    gcb G_DRAW_ALPHA
    gflush

    # 1x32
    glsi SPRITE_1x32
    gcb G_DRAW
    gflush

    glsd r5 G_1x32
    gmvi 31 0
    gcb G_DRAW_ALPHA
    gflush

    halt