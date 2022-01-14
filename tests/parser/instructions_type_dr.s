A:
    blti r1 123 B
    blti 234 r2 B
B:
    blei 123 r5 C
    blei r3 234 C
C:
    bgti r1 123 D
    bgti 234 r2 D
D:
    bgei 123 r5 A
    bgei r3 234 A