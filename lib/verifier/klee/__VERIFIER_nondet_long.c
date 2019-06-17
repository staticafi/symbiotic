#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

long __VERIFIER_nondet_long(void)
{
	long x;
	klee_make_symbolic(&x, sizeof(x), "nondet-long");
	return x;
}
