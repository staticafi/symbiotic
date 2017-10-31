#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

unsigned int __VERIFIER_nondet_unsigned_named(const char *name)
{
	unsigned int x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
