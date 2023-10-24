#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

float __symbiotic_nondet_float(void)
{
	_Bool nan_choice;
	klee_make_symbolic(&nan_choice, sizeof(_Bool), "nondet_float_is_nan");
	if (nan_choice) {
		return ((float)0.0)/0.0;
	} else {
		float x;
		klee_make_symbolic(&x, sizeof(x), "nondet-float");
		return x;
	}
}
