#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

double __VERIFIER_nondet_double_named(const char *name)
{
	double x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
