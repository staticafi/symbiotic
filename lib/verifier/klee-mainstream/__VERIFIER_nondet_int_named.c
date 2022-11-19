#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

int __symbiotic_nondet_int_named(const char *name)
{
	int x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
