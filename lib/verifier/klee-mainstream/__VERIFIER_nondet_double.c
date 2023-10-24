#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

double __symbiotic_nondet_double(void)
{
	_Bool nan_choice;
	klee_make_symbolic(&nan_choice, sizeof(_Bool), "nondet_double_is_nan");
	if (nan_choice) {
		return ((double)0.0)/0.0;
	} else {
		double x;
		klee_make_symbolic(&x, sizeof(x), "nondet-double");
		return x;
	}
}
