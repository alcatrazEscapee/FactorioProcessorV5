# Pong

include "./7seg_numbers.s"
texture TEXTURE_PONG "./textures/pong.png"

sprite SPRITE_TEXT_YOU TEXTURE_PONG [ 0 0 22 7 ]
sprite SPRITE_TEXT_LOSE TEXTURE_PONG [ 0 6 22 7 ]
sprite SPRITE_TEXT_WIN TEXTURE_PONG [ 0 13 22 7 ]

alias WINNING_SCORE 4  # Score needed to win, must be <= 10

alias TICK_DELTA 100

alias BALL_WIDTH 2
alias PADDLE_HEIGHT 6

alias MIN_PADDLE_Y 0
alias MAX_PADDLE_Y 26 # 32 - 6

word nextTick
word ballX, ballY
word ballVX, ballVY
word playerX, playerY
word computerX, computerY
word playerScore, computerScore

# Memory locations used for peripheral IO
# Cannot use the literal value in instructions, so these have to be preloaded
word COUNTER, CONTROL_UP, CONTROL_DOWN
word RNG

sprite SPRITE_PADDLE `
#.....
#.....
#.....
#.....
#.....
#.....
`

sprite SPRITE_BALL `
##
##
`

main:
    # First-Time
    seti @COUNTER 2000
    seti @CONTROL_UP 3000
    seti @CONTROL_DOWN 3001
    seti @RNG 4000

    seti @playerScore 0
    seti @computerScore 0

main_restart:
    # Initialization
    seti @ballX 15
    seti @ballY 15
    seti @playerX 1
    seti @playerY 12
    seti @computerX 30
    seti @computerY 12
    addi @nextTick @@COUNTER TICK_DELTA  # First tick

    # Random X/Y Velocity Signs
    # 1 - (RNG & 0b10) gives 1 or -1 in *minimal instructions*
    andi r1 @@RNG 0b10
    subi @ballVX 1 r1

    andi r1 @@RNG 0b10
    subi @ballVY 1 r1

main_loop:

main_ai_move:
    blti @ballX 15 main_player_move
    addi r1 @computerY 2
    beq r1 @ballY main_player_move
    bgt r1 @ballY main_ai_move_down
main_ai_move_up:
    blei @computerY MIN_PADDLE_Y main_player_move
    subi @computerY @computerY 1
    br main_player_move
main_ai_move_down:
    bgei @computerY MAX_PADDLE_Y main_player_move
    addi @computerY @computerY 1

main_player_move:
    bnei @@CONTROL_UP 1 main_player_move_after_up
    blei @playerY MIN_PADDLE_Y main_player_move_after_up
    subi @playerY @playerY 1
main_player_move_after_up:

    bnei @@CONTROL_DOWN 1 main_player_move_after_down
    bgei @playerY MAX_PADDLE_Y main_player_move_after_down
    addi @playerY @playerY 1
main_player_move_after_down:

main_ball_move:
    bnei @ballVY 1 main_ball_move_up

main_ball_move_down:
    bnei @ballY 30 main_ball_move_left_right
    muli @ballVY @ballVY -1
    br main_ball_move_left_right

main_ball_move_up:
    bnei @ballY 0 main_ball_move_left_right
    muli @ballVY @ballVY -1

main_ball_move_left_right:
    beqi @ballVX 1 main_ball_move_right

main_ball_move_left:
    bnei @ballX 2 main_ball_move_all_done
    sub r1 @ballY @playerY
    blti r1 -1 main_ball_move_all_done
    bgti r1 6 main_ball_move_all_done
    muli @ballVX @ballVX -1
    br main_ball_move_all_done

main_ball_move_right:
    bnei @ballX 28 main_ball_move_all_done
    sub r1 @ballY @computerY
    blei r1 -1 main_ball_move_all_done
    bgti r1 6 main_ball_move_all_done
    muli @ballVX @ballVX -1

main_ball_move_all_done:
    add @ballX @ballX @ballVX
    add @ballY @ballY @ballVY

main_check_win:
    bnei @ballX 0 main_check_win_1
    addi @computerScore @computerScore 1
    bgei @computerScore WINNING_SCORE main_display_loss
    br main_restart
main_check_win_1:
    bnei @ballX 30 main_graphics
    addi @playerScore @playerScore 1
    bgei @playerScore WINNING_SCORE main_display_win
    br main_restart

main_graphics:
    gcb G_CLEAR  # Clear screen
    glsi SPRITE_PADDLE  # Player paddle
    gmv @playerX @playerY
    gcb G_DRAW_ALPHA
    glsi SPRITE_PADDLE  # Computer paddle
    gmv @computerX @computerY
    gcb G_DRAW_ALPHA
    glsi SPRITE_BALL  # Ball
    gmv @ballX @ballY
    gcb G_DRAW_ALPHA
    addi r1 @playerScore SPRITE_DIGITS  # Player score (0-9)
    gls r1
    gmvi 11 1
    gcb G_DRAW_ALPHA
    addi r1 @computerScore SPRITE_DIGITS  # Computer score (0-9)
    gls r1
    gmvi 18 1
    gcb G_DRAW_ALPHA
    gflush

main_wait:
    sub r1 @nextTick @@COUNTER
    bgti r1 0 main_wait
    addi @nextTick @@COUNTER TICK_DELTA
    br main_loop

main_display_loss:
    gcb G_CLEAR
    glsi SPRITE_TEXT_YOU
    gmvi 5 4
    gcb G_DRAW_ALPHA
    glsi SPRITE_TEXT_LOSE
    gmvi 5 18
    gcb G_DRAW_ALPHA
    gflush
    halt

main_display_win:
    gcb G_CLEAR
    glsi SPRITE_TEXT_YOU
    gmvi 5 4
    gcb G_DRAW_ALPHA
    glsi SPRITE_TEXT_WIN
    gmvi 5 18
    gcb G_DRAW_ALPHA
    gflush
    halt