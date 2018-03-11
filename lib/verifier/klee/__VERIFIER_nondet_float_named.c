#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

float __VERIFIER_nondet_float_named(const char *name)
{
	_Bool nan_choice;
	klee_make_symbolic(&nan_choice, sizeof(_Bool), "nondet_float_is_nan");
	if (nan_choice) {
		return ((float)0.0)/0.0;
	} else {
		float x;
		klee_make_symbolic(&x, sizeof(x), name);
		return x;
	}
}
