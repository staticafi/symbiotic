#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

unsigned int __VERIFIER_nondet_U32(void)
{
	unsigned int x;
	klee_make_symbolic(&x, sizeof(x), "nondet-u32");
	return x;
}
