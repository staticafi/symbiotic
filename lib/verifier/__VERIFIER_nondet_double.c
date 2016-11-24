#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

double __VERIFIER_nondet_double(void)
{
	double x;
	klee_make_symbolic(&x, sizeof(x), "nondet-double");
	return x;
}
