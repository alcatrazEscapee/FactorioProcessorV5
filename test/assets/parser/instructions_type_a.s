alias X 123
alias Y 432

add r1 r2 r3
sub @r1 r2 r3
mul @10 r2 r3
div @r1.4 r2 r3
pow @@10.4 r2 r3
mod @X r2 r3
and @@X r2 r3
or @@X.4 r2 r3
nand r1 @r2 r3
nor r1 @10 r3
xor r1 @r4.5 r3
xnor r1 @@10.4 r3
ls r5 @X r3
rs r5 @@X r3
eq r5 @@X.4 r3
ne r4 r5 r6
lt sp ra rv
gt @sp @ra @rv