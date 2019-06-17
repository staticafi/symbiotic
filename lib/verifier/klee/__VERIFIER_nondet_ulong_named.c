#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

unsigned long __VERIFIER_nondet_ulong_named(const char *name)
{
	unsigned long x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
