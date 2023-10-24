#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

long __symbiotic_nondet_loff_t(void)
{
	long long x;
	klee_make_symbolic(&x, sizeof(x), "nondet-loff_t");
	return x;
}
