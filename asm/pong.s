# Pong

alias TICK_DELTA 100

alias BALL_WIDTH 2
alias PADDLE_HEIGHT 6

word nextTick
word ballX, ballY
word ballVX, ballVY
word playerX, playerY
word computerX, computerY
word playerScore, computerScore

# Memory locations used for peripheral IO
# Cannot use the literal value in instructions, so these have to be preloaded
word COUNTER, CONTROL_UP, CONTROL_DOWN

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

    # Initialization
    seti @ballX 15
    seti @ballY 15
    seti @ballVX 1
    seti @ballVY 1
    seti @playerX 1
    seti @playerY 12
    seti @computerX 30
    seti @computerY 12

main_loop:

main_ai_move:
    blti @ballX 15 main_player_move
    addi r1 @computerY 2
    beq r1 @ballY main_player_move
    bgt r1 @ballY main_ai_move_down
main_ai_move_up:
    subi @computerY @computerY 1
    br main_player_move
main_ai_move_down:
    addi @computerY @computerY 1

main_player_move:
    bnei @@CONTROL_UP 1 main_player_move_down
    subi @playerY @playerY 1
    br main_player_move_end
main_player_move_down:
    bnei @@CONTROL_DOWN 1 main_player_move_end
    addi @playerY @playerY 1
main_player_move_end:

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
    br main
main_check_win_1:
    bnei @ballX 30 main_graphics
    addi @playerScore @playerScore 1
    br main
main_graphics:
    # Clear Screen -> Draw Player -> Draw Computer -> Draw Ball -> Flush
    gcb G_CLEAR
    glsi SPRITE_PADDLE
    gmv @playerX @playerY
    gcb G_DRAW_ALPHA
    glsi SPRITE_PADDLE
    gmv @computerX @computerY
    gcb G_DRAW_ALPHA
    glsi SPRITE_BALL
    gmv @ballX @ballY
    gcb G_DRAW_ALPHA
    gflush

main_wait:
    sub r1 @nextTick @@COUNTER
    bgti r1 0 main_wait
    addi @nextTick @@COUNTER TICK_DELTA
    br main_loop