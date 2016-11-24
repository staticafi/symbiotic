#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

float __VERIFIER_nondet_float(void)
{
	float x;
	klee_make_symbolic(&x, sizeof(x), "nondet-float");
	return x;
}
