#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

char __symbiotic_nondet_char(void)
{
	char x;
	klee_make_symbolic(&x, sizeof(x), "nondet-char");
	return x;
}
