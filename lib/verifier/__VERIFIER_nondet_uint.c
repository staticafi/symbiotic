#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

unsigned int __VERIFIER_nondet_uint(void)
{
	unsigned int x;
	klee_make_symbolic(&x, sizeof(x), "nondet-uint");
	return x;
}
