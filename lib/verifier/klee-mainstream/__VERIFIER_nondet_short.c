#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

short __VERIFIER_nondet_short(void)
{
	short x;
	klee_make_symbolic(&x, sizeof(x), "nondet-short");
	return x;
}
