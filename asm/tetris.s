# Tetris
#[sim_clock_time=500us]

include "./stdio.s"
include "./7seg_numbers.s"

texture TEXTURE_BACKGROUND "./textures/tetris_background.png"
texture TEXTURE_LOADING "./textures/tetris_loading.png"
texture TEXTURE_START "./textures/tetris_start.png"

sprite SPRITE_BACKGROUND TEXTURE_BACKGROUND [ 0 0 32 32 ]
sprite SPRITE_LOADING TEXTURE_LOADING [ 0 0 32 32 ]
sprite SPRITE_START TEXTURE_START [ 0 0 32 32 ]


# ======================= Loading + Start Screens ==================================
# Load screen is drawn with minimal bootstrapping
# Setup code is invoked for the main game
# Start screen is then drawn, and a polling loop is used on the main start button

inline draw_loading_screen:
    glsi SPRITE_LOADING
    gcb G_DRAW
    gflush
    ret  # draw_loading_screen

inline draw_start_screen:
    glsi SPRITE_START
    gcb G_DRAW
    gflush
    ret  # draw_start_screen


# ========================== Game Initialization and Setup =========================
# All main game logic needs to be zero'd and initialized here
#
# Note:
# Both pieces, and the game board (rows) are indexed with LSB = left and MSB = right
# This is done as the GPU uses LSB...MSB ordering for glsd instructions


word [28] pieces  # 7 Pieces x 4 Rotations : Index is pieces[piece << 2 | rotation]

word [4] bottomRows # Extra rows, used for masking off the length of the board
word [20] rows      # Tetris board, minus the falling piece. rows[0] is the bottom row that squares can place in
word [2] topRows    # Extra rows, used for masking off the length of the board 

word [4] fullRows  # Indexes of rows that are full, and need to be removed
word fullRowMask  # Just the full row, used for flashing when a row is complete

word pieceX, pieceY  # (6, 0) is the position at which a piece spawns. Coordinates are in quadrant IV semantics (so +x >, +y \/ )
word pieceType, nextPieceType
word pieceRotation
word pieceIndex

word mainLoopIteration, mainLoopMaxTimer
word mainLoopNextPieceFlag

word score
word [5] scoreValues  # Values of completing 1, 2, 3 or 4 rows at once

# Locals
word pointer, next_pointer

# Memory locations used for peripheral IO
# Cannot use the literal value in instructions, so these have to be preloaded
word COUNTER, CONTROL_UP, CONTROL_DOWN, CONTROL_LEFT, CONTROL_RIGHT, CONTROL_X
word RNG



alias FULL_ROW  0b111111111111  # 10-bit wide, + 2-bit walls
alias EMPTY_ROW 0b100000000001
alias FULL_ROW_NO_WALLS 0b011111111110  # 10-bit wide

alias PIECE_O     0b0000_0110_0110_0000  # 0
alias PIECE_I     0b0100_0100_0100_0100  # 1
alias PIECE_I_90  0b0000_1111_0000_0000
alias PIECE_S     0b0000_0011_0110_0000  # 2
alias PIECE_S_90  0b0000_0100_0110_0010
alias PIECE_Z     0b0000_0110_0011_0000  # 3
alias PIECE_Z_90  0b0000_0010_0110_0100
alias PIECE_L     0b0000_0110_0010_0010  # 4
alias PIECE_L_90  0b0000_0001_0111_0000
alias PIECE_L_180 0b0000_0010_0010_0011
alias PIECE_L_270 0b0000_0000_0111_0100
alias PIECE_J     0b0000_0011_0010_0010  # 5
alias PIECE_J_90  0b0000_0000_0111_0001
alias PIECE_J_180 0b0000_0010_0010_0110
alias PIECE_J_270 0b0000_0100_0111_0000
alias PIECE_T     0b0000_0010_0111_0000  # 6
alias PIECE_T_90  0b0000_0010_0011_0010
alias PIECE_T_180 0b0000_0000_0111_0010
alias PIECE_T_270 0b0000_0010_0110_0010

alias MAIN_LOOP_MAX_TIMER 5


# ========================= Setup / Initialization ============================

inline first_time_setup:

    # Constants
    seti @fullRowMask   FULL_ROW_NO_WALLS
    
    seti @CONTROL_UP    PORT_CONTROL_UP
    seti @CONTROL_DOWN  PORT_CONTROL_DOWN
    seti @CONTROL_LEFT  PORT_CONTROL_LEFT
    seti @CONTROL_RIGHT PORT_CONTROL_RIGHT
    seti @CONTROL_X     PORT_CONTROL_X
    seti @COUNTER       PORT_COUNTER
    seti @RNG           PORT_RANDOM

    # Build pieces[] array
    seti @pieces[0]  PIECE_O
    seti @pieces[1]  PIECE_O
    seti @pieces[2]  PIECE_O
    seti @pieces[3]  PIECE_O
    seti @pieces[4]  PIECE_I
    seti @pieces[5]  PIECE_I_90
    seti @pieces[6]  PIECE_I
    seti @pieces[7]  PIECE_I_90
    seti @pieces[8]  PIECE_S
    seti @pieces[9]  PIECE_S_90
    seti @pieces[10] PIECE_S
    seti @pieces[11] PIECE_S_90
    seti @pieces[12] PIECE_Z
    seti @pieces[13] PIECE_Z_90
    seti @pieces[14] PIECE_Z
    seti @pieces[15] PIECE_Z_90
    seti @pieces[16] PIECE_L
    seti @pieces[17] PIECE_L_90
    seti @pieces[18] PIECE_L_180
    seti @pieces[19] PIECE_L_270
    seti @pieces[20] PIECE_J
    seti @pieces[21] PIECE_J_90
    seti @pieces[22] PIECE_J_180
    seti @pieces[23] PIECE_J_270
    seti @pieces[24] PIECE_T
    seti @pieces[25] PIECE_T_90
    seti @pieces[26] PIECE_T_180
    seti @pieces[27] PIECE_T_270

    # Initialize bottom rows (constants) and main rows (empty)
    # Bottom rows are all full
    seti @bottomRows[0] FULL_ROW
    seti @bottomRows[1] FULL_ROW
    seti @bottomRows[2] FULL_ROW
    seti @bottomRows[3] FULL_ROW

    # Main rows are all empty
    seti @rows[0]  EMPTY_ROW
    seti @rows[1]  EMPTY_ROW
    seti @rows[2]  EMPTY_ROW
    seti @rows[3]  EMPTY_ROW
    seti @rows[4]  EMPTY_ROW
    seti @rows[5]  EMPTY_ROW
    seti @rows[6]  EMPTY_ROW
    seti @rows[7]  EMPTY_ROW
    seti @rows[8]  EMPTY_ROW
    seti @rows[9]  EMPTY_ROW
    seti @rows[10] EMPTY_ROW
    seti @rows[11] EMPTY_ROW
    seti @rows[12] EMPTY_ROW
    seti @rows[13] EMPTY_ROW
    seti @rows[14] EMPTY_ROW
    seti @rows[15] EMPTY_ROW
    seti @rows[16] EMPTY_ROW
    seti @rows[17] EMPTY_ROW
    seti @rows[18] EMPTY_ROW
    seti @rows[19] EMPTY_ROW
	
	# Top rows are all empty
	seti @topRows[0] EMPTY_ROW
	seti @topRows[1] EMPTY_ROW
	
	# scoreValues Array
	seti @scoreValues[0] 0
	seti @scoreValues[1] 1
	seti @scoreValues[2] 3
	seti @scoreValues[3] 8
	seti @scoreValues[4] 30

    # Default values for variables
    seti @score 0
	seti @mainLoopIteration 0
	seti @mainLoopMaxTimer MAIN_LOOP_MAX_TIMER
	seti @mainLoopNextPieceFlag 0
	
	# Game variables
	andi @pieceType @@RNG 0xffff         # pieceType = random() & 0xffff
	modi @pieceType @pieceType 7         # pieceType %= 7
	andi @nextPieceType @@RNG 0xffff     # nextPieceType = random() & 0xffff
	modi @nextPieceType @nextPieceType 7 # nextPieceType %= 7
	seti @pieceRotation 0                # Default piece rotation, x, y
	seti @pieceX 6
	seti @pieceY 0

    ret  # first_time_setup


# ============================= Main Game Functions ===============================
# All main game functionality resides here


inline intersect_piece_with_board:
	# Intersects the current piece at (@pieceX, @pieceY, @pieceType, @pieceRotation) with the board
	# Updates the rows[] variables
	
	subi r1 rows[20] @pieceY  # Set the initial @r1 = rows[pieceY] pointer
	
	lsi  r4 @pieceType 2      # get the piece index from pieceType, pieceRotation
	or   r4 r4 @pieceRotation
	addi r4 r4 pieces         # @r4 = pieces[the current piece]
	
	addi r3 @pieceX 2         # r3 = a positive shift right, into the board by 4
	
	# Slice 0
	andi r2 @r4 0b1111        # r2 = the four bits of pieces in this row
	ls   r2 r2 r3             # r2 << r3, shift poportional to the @pieceX
	rsi  r2 r2 4	          # r2 >>= 4, shift back into the same radix as rows
	
	or   @r1 @r1 r2           # @r1 |= r2, OR the existing row with the piece
	
	# Slice 1
	subi r1 r1 1			  # r1--;
		
	rsi  r2 @r4 4             # r2 = the four bits of pieces in this row
	andi r2 r2 0b1111
	ls   r2 r2 r3             # r2 << r3, shift poportional to the @pieceX
	rsi  r2 r2 4	          # r2 >>= 4, shift back into the same radix as rows
	
	or   @r1 @r1 r2           # @r1 |= r2, OR the existing row with the piece
	
	# Slice 2
	subi r1 r1 1			  # r1--;

	rsi  r2 @r4 8             # r2 = the four bits of pieces in this row
	andi r2 r2 0b1111
	ls   r2 r2 r3             # r2 << r3, shift poportional to the @pieceX
	rsi  r2 r2 4	          # r2 >>= 4, shift back into the same radix as rows
	
	or   @r1 @r1 r2           # @r1 |= r2, OR the existing row with the piece
	
	# Slice 3
	subi r1 r1 1			  # r1--;

	rsi  r2 @r4 12            # r2 = the four bits of pieces in this row
	ls   r2 r2 r3             # r2 << r3, shift poportional to the @pieceX
	rsi  r2 r2 4	          # r2 >>= 4, shift back into the same radix as rows
	
	or   @r1 @r1 r2           # @r1 |= r2, OR the existing row with the piece
	
	ret


inline check_for_intersection_with_board:
    # r11 = prospective piece X
    # r12 = prospective piece Y
	# @pieceType = piece type
	# r14 = prospective piece rotation
    # Sets rv = 1 if the piece can be moved to this position, 0 if not
	
	# Only needs to check four rows, the ones in the 4x4 region of the piece
	# Each row is repeated, with different constants
	
	subi r4 rows[20] r12  # Set the initial @r4 = rows[pieceY] pointer
	
	lsi  r5 @pieceType 2  # get the piece index from @pieceType, r14 (pieceRotation)
	or   r5 r5 r14
	addi r5 r5 pieces     # @r5 = pieces[the current piece]
		
	# Slice 0
	lsi  r1 @r4 4      # Shift left by four, so we can right shift the piece and not deal with negative shifts
	andi r2 @r5 0b1111 # r2 = the four bits of pieces in this row
	addi r3 r11 2
	ls   r2 r2 r3      # r2 = the four bits of pieces in this row, shifted to the same space as the row
		
	and  r3 r1 r2      # r3 = any bits that collide
	set  rv r3         # rv = r3 (initial condition)
		
	# Slice 1
	subi r4 r4 1	   # r4--;
	
	lsi  r1 @r4 4      # Shift left by four, so we can right shift the piece and not deal with negative shifts
	rsi  r2 @r5 4      # r2 = the four bits of pieces in this row
	andi r2 r2 0b1111
	addi r3 r11 2
	ls   r2 r2 r3      # r2 = the four bits of pieces in this row, shifted to the same space as the row
	
	and  r3 r1 r2      # r3 = any bits that collide
	or   rv rv r3      # rv |= r3
		
	# Slice 2
	subi r4 r4 1	   # r4--;
	
	lsi  r1 @r4 4      # Shift left by four, so we can right shift the piece and not deal with negative shifts
	rsi  r2 @r5 8      # r2 = the four bits of pieces in this row
	andi r2 r2 0b1111
	addi r3 r11 2
	ls   r2 r2 r3      # r2 = the four bits of pieces in this row, shifted to the same space as the row
	
	and  r3 r1 r2      # r3 = any bits that collide
	or   rv rv r3      # rv |= r3
		
	# Slice 3
	subi r4 r4 1	   # r4--;
	
	lsi  r1 @r4 4      # Shift left by four, so we can right shift the piece and not deal with negative shifts
	rsi  r2 @r5 12     # r2 = the four bits of pieces in this row
	addi r3 r11 2
	ls   r2 r2 r3      # r2 = the four bits of pieces in this row, shifted to the same space as the row
	
	and  r3 r1 r2      # r3 = any bits that collide
	or   rv rv r3      # rv |= r3
		
	eqi  rv rv 0       # rv = rv == 0, so 1 = valid, and 0 = invalid
    ret


inline check_for_completed_rows:
    # Checks for rows that have been completed
    # Only needs to check for up to five rows, storing the completed indices in @fullRows
    # The last row can never be completed and so this saves an additional loop iteration
    # Modifies the rows variable, cascading down rows by removing completed ones
    # Clobbers @pointer, @next_pointer
    # Returns: count of full rows in r1 (score)

    seti r1 0  # counter
    seti @pointer rows
    seti @next_pointer rows

    # Clear fullRows
    seti @fullRows[0] -99
    seti @fullRows[1] -99
    seti @fullRows[2] -99
    seti @fullRows[3] -99

check_for_completed_rows_loop:
    bnei @@pointer FULL_ROW check_for_completed_rows_skip

    addi r1 r1 1  # Increment counter
    subi @next_pointer @next_pointer 1  # Copy over current row

    addi r2 r1 fullRows  # & fullRows[r1]
    subi @r2 @pointer rows  # obtain index of row from pointer

    br check_for_completed_rows_next

check_for_completed_rows_skip:
    set @@next_pointer @@pointer # Copy row if not complete

check_for_completed_rows_next:

    # Increment and loop
    addi @pointer @pointer 1
    addi @next_pointer @next_pointer 1
    blti @pointer rows[20] check_for_completed_rows_loop

    # Copy zeros, top down, for rows that were not copied into due to being complete
    seti r2 0
    beq r1 r0 check_for_completed_rows_none
check_for_completed_rows_top_loop:
    subi @pointer rows[19] r2
    seti @@pointer 0

    # Increment and loop
    addi r2 r2 1
    blt r2 r1 check_for_completed_rows_top_loop

check_for_completed_rows_none:
    ret


inline wait_for_key_x:
    # Waits for the 'X' key to be pressed
wait_for_key_x_loop:
    beqi @@CONTROL_X 0 wait_for_key_x_loop
    ret

inline wait_200ms:
	# Waits approximately an absolute 200ms @ sim_clock_time=500us
	seti r1 200
wait_200ms_loop:
	subi r1 r1 1
	bgti r1 0 wait_200ms_loop
	ret



# =============================== Main Game Draw Loop ===============================

inline draw_game:
    # Draws all main game sprites
    # Invoked from main loop
    # Uses @pointer

    glsi SPRITE_BACKGROUND
    gcb G_DRAW

    # Draw the piece rows
    seti @pointer rows
    seti r1 2
    seti r2 27
draw_game_loop:
    glsd @@pointer G_32x1  # And is now placed at the origin
    gmv r1 r2  # Then translated the correct amount
    gcb G_DRAW_ALPHA

    # Increment and loop
    addi @pointer @pointer 1
    subi r2 r2 1
    blti @pointer rows[20] draw_game_loop

    # Draw the currently falling piece
    lsi  r1 @pieceType 2      # r1 = piece index
    or   r1 r1 @pieceRotation
    addi r1 r1 pieces         # @r1 = pieces[pieceType, pieceRotation]
    glsd @r1 G_4x8
    addi r1 0 @pieceX         # Calculate screen position
    addi r2 7 @pieceY
    gmv  r1 r2
	gcb  G_DRAW_ALPHA
	
	# Draw the next piece graphic
	lsi  r1 @nextPieceType 2  # r1 = piece index
	addi r1 r1 pieces         # @r1 = pieces[nextPieceType, 0]
	glsd @r1 G_4x8
	gmvi 19 10
	gcb  G_DRAW_ALPHA

    # Draw Score, each digit
    modi r2 @score 10
    divi r3 @score 10
    addi r1 r2 SPRITE_DIGITS
    gls r1
    gmvi 25 24
    gcb G_DRAW_ALPHA

    modi r2 r3 10
    divi r3 r3 10
    addi r1 r2 SPRITE_DIGITS
    gls r1
    gmvi 21 24
    gcb G_DRAW_ALPHA

    modi r2 r3 10
    addi r1 r2 SPRITE_DIGITS
    gls r1
    gmvi 17 24
    gcb G_DRAW_ALPHA

    gflush
    ret


inline draw_completed_rows_flash:
    # Draws and runs the animation of filled rows flashing
    # Expects fullRows to be initialized to indexes of rows that need to flash
    # Masks + Toggles the affected rows once, multiple invocations in sequence are required to do the animation

    seti @pointer fullRows
    seti r1 2
    seti r2 27
draw_completed_rows_flash_loop:
    subi r2 27 @@pointer  # Invalid row -> @@pointer will be very negative, as a result the image will be empty
    glsd @fullRowMask G_32x1  # Mask the row
    gmv r1 r2  # Translate over the existing row
    gcb G_TOGGLE  # Toggle what is already there

    # Increment and loop
    addi @pointer @pointer 1
    subi r2 r2 1
    blti @pointer fullRows[4] draw_completed_rows_flash_loop

    gflush
    ret


# =============================== Entry Point =================================


main:
    call draw_loading_screen    # Display loading screen before bootstrapping
    call first_time_setup       # Initialize memory
    call draw_start_screen      # Switch to displaying the start screen
    call wait_for_key_x         # Wait for the 'x' key to be pressed to start game

main_loop:

	# If no piece currently selected, then generate a new piece.
	# Do an immediate piece check if the game should end, if so, branch out of loop and to game end animation
	# If not, Branch immediately to end of loop
	bnei @mainLoopNextPieceFlag 1 main_loop_no_next_piece
	
	# Before placing a new piece, we have to check the board for intersections, possibly animate the current rows dissapearing, then display the new piece
	call check_for_completed_rows    # r1 = count of completed rows ('rows' is modified)
	
	# If there are no completed rows, branch after the animation
	# If there are completed rows, we need to increment score
	beqi r1 0 main_no_completed_rows
	
	# Increment score
	addi r2 r1 scoreValues  # @r2 = scoreValues[r1]
	add  @score @score @r2  # @score += scoreValues[r1]
	
	# Animate the rows flashing
	call draw_completed_rows_flash
	call wait_200ms
	call draw_completed_rows_flash
	call wait_200ms
	call draw_completed_rows_flash
	call wait_200ms
	call draw_completed_rows_flash
	call wait_200ms
	call draw_completed_rows_flash
	call wait_200ms
	call draw_completed_rows_flash
	call wait_200ms
	
	# Re-draw the game first, because we need to be able to see the new modified rows
	call draw_game

main_no_completed_rows:
	# Generate the new piece
	seti @pieceX 6                            # Reset pieceX, pieceY
	seti @pieceY 0
	set  @pieceType @nextPieceType            # pieceType = nextPieceType
	seti @pieceRotation 0                     # Reset pieceRotation
	andi @nextPieceType @@RNG 0xffff          # nextPieceType = random() & 0xffff (to prevent negative values)
	modi @nextPieceType @nextPieceType 7      # nextPieceType %= 7
	seti @mainLoopNextPieceFlag 0             # mainLoopNextPieceFlag = False
	
	# Check to see if the next piece immediately intersects with the board, if it does, end game
	set  r11 @pieceX                          # Copy piece into temporaries
	set  r12 @pieceY
	set  r14 @pieceRotation
	call check_for_intersection_with_board    # rv = 1 if piece is valid
	beqi rv 0 main_end_game                   # go to main_end_game if piece is invalid
	br   main_wait_for_next_tick              # otherwise advance to next tick

main_loop_no_next_piece:
	# If on Nth cycle (or the 'down' key is pressed), then attempt to move down
	# If move down is valid, then do move, then branch to end of loop
	# Otherwise, halt piece
	beq  @mainLoopIteration @mainLoopMaxTimer main_yes_move_down
	beqi @@CONTROL_DOWN 1 main_yes_move_down
	br   main_no_move_down
main_yes_move_down:
	
	seti @mainLoopIteration 0  # mainLoopIteration = 0, reset loop
	
	set  r11 @pieceX           # Copy the moved-down piece into parameter variables
	addi r12 @pieceY 1
	set  r14 @pieceRotation
	
	call check_for_intersection_with_board  # rv = 1 if moved-down piece is valid
	
	beqi rv 0 main_move_down_halt           # branch to halt if we are blocked from moving down
	addi @pieceY @pieceY 1					# @pieceY -= 1
	br main_wait_for_next_tick              # moved down, so branch and wait for next tick
main_move_down_halt:
	call intersect_piece_with_board         # Mask the current piece into the rows variables
		
	seti @mainLoopNextPieceFlag 1           # @mainLoopNextPieceFlag = True
	br main_wait_for_next_tick              # halted piece, so branch and wait for next tick


	# Not moving down, so check for either left / right motion, or a rotation, caused by keys
main_no_move_down:
	# Copy current piece into temporaries
	set r11 @pieceX
	set r12 @pieceY
	set r14 @pieceRotation
	
	beqi @@CONTROL_UP 0 main_no_rotate  # Check rotation
	addi r14 r14 1
	modi r14 r14 4
main_no_rotate:

	beqi @@CONTROL_LEFT 0 main_no_move_left  # Check left + right movements
	addi r11 r11 -1
main_no_move_left:
	beqi @@CONTROL_RIGHT 0 main_no_move_right
	addi r11 r11 1
main_no_move_right:

	call check_for_intersection_with_board  # See if the prospective new piece location and rotation is valid
	
	beqi rv 0 main_cannot_move_or_rotate
	set @pieceX r11         # Copy the changed piece to the actual piece state
	set @pieceY r12
	set @pieceRotation r14

main_cannot_move_or_rotate:
	
main_wait_for_next_tick:                          # Wait for tick, then loop back to beginning

	addi @mainLoopIteration @mainLoopIteration 1  # @mainLoopIteration++
    call draw_game                                # Re-draw game
	br   main_loop


main_end_game:
	call draw_game  # Draw the final board state, with the overlapping piece
    halt
