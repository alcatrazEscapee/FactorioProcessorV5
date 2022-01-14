# Computes several fibonacci numbers and stores the sequence in memory
# 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368


# Data
alias HEAD 20  # Arbitrary spot into memory
alias TAIL 44

# Variables
alias pointer 1
alias x 2
alias y 3
alias temp 4

main:
    seti @x 0
    seti @y 1
    seti @pointer HEAD
loop:
    set @@pointer @x
    add @temp @x @y  # compute next
    set @x @y  # shift over by one
    set @y @temp
    addi @pointer @pointer 1
    blei @pointer TAIL loop  # loop while not at the end
checks:
    # Check a couple values
    assert @20 = 0
    assert @21 = 1
    assert @22 = 1
    assert @23 = 2
    assert @42 = 17711
    assert @43 = 28657
    assert @44 = 46368
    halt
