#include <stdio.h>

int __symbiotic_nondet_int(void);
char __symbiotic_nondet_char(void);
void __VERIFIER_assume(int);

extern void klee_make_symbolic(void *, size_t, const char *);

char *fgets(char *restrict s, int size, FILE *restrict stream) {
    *stream; /* test the pointer */

    int rs = __symbiotic_nondet_int();
    __VERIFIER_assume(rs >= 0 && rs < size);
    for (int i = 0; i < rs; ++i)
        s[i] = __symbiotic_nondet_char();
    s[rs] = '\0';

    if (__symbiotic_nondet_int() == 0)
        return NULL;
    return s;
}


