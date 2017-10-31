#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

float __VERIFIER_nondet_float_named(const char *name)
{
	float x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
