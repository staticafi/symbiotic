#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

unsigned short __VERIFIER_nondet_ushort_named(const char *name)
{
	unsigned short x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
