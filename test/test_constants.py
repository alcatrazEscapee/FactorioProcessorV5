from constants import GPUFunction


def test_g_clear(): run(GPUFunction.G_CLEAR, '........')
def test_g_nor(): run(GPUFunction.G_NOR, '.....###')
def test_g_erase(): run(GPUFunction.G_ERASE, '###.....')
def test_g_draw_negative(): run(GPUFunction.G_DRAW_NEGATIVE, '###..###')
def test_g_highlight(): run(GPUFunction.G_HIGHLIGHT, '....#...')
def test_g_negative(): run(GPUFunction.G_NEGATIVE, '....####')
def test_g_toggle(): run(GPUFunction.G_TOGGLE, '###.#...')
def test_g_nand(): run(GPUFunction.G_NAND, '###.####')
def test_g_erase_negative(): run(GPUFunction.G_ERASE_NEGATIVE, '...#....')
def test_g_toggle_negative(): run(GPUFunction.G_TOGGLE_NEGATIVE, '...#.###')
def test_g_noop(): run(GPUFunction.G_NOOP, '####....')
def test_g_draw_alpha_negative(): run(GPUFunction.G_DRAW_ALPHA_NEGATIVE, '####.###')
def test_g_draw(): run(GPUFunction.G_DRAW, '...##...')
def test_g_highlight_negative(): run(GPUFunction.G_HIGHLIGHT_NEGATIVE, '...#####')
def test_g_draw_alpha(): run(GPUFunction.G_DRAW_ALPHA, '#####...')
def test_g_full(): run(GPUFunction.G_FULL, '########')


def run(f: GPUFunction, expected: str):
    left = '####....'
    right = '...##...'
    actual = ''.join(f.apply_str(lhs, rhs) for lhs, rhs in zip(left, right))
    assert actual == expected, 'Left    : %s\nRight   : %s\nExpected: %s\nActual  : %s' % (left, right, expected, actual)