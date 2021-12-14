#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

long __symbiotic_nondet_long_named(const char *name)
{
	long x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
