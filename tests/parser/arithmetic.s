# Tests various arithmetic capabilities

# Some addresses
alias X 100
alias Y 101
alias Z 102

# Initialize some numeric values
seti @X 7
seti @Y 13

# Perform some basic arithmetic operations
add @X @Y @Z
assert @Z = 20

sub @Y @X @Z
assert @Z = 6

sub @X @Y @Z
assert @Z = -6

mul @X @Y @Z
assert @Z = 91

div @X @Y @Z
assert @Z = 0

div @Y @X @Z
assert @Z = 1

seti @Y 2

pow @X @Y @Z
assert @Z = 49

seti @Y 13

mod @X @Y @Z
assert @Z = 0

mod @Y @X @Z
assert @Z = 6

halt 0

