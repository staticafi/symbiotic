#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

double __VERIFIER_nondet_double_named(const char *name)
{
	_Bool nan_choice;
	klee_make_symbolic(&nan_choice, sizeof(_Bool), "nondet_double_is_nan");
	if (nan_choice) {
		return ((double)0.0)/0.0;
	} else {
		double x;
		klee_make_symbolic(&x, sizeof(x), name);
		return x;
	}
}
