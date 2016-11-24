#include "symbiotic-size_t.h"

int __VERIFIER_nondet_size_t(void)
{
	size_t x;
	klee_make_symbolic(&x, sizeof(x), "nondet-size_t");
	return x;
}
