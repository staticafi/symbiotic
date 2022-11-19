#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

_Bool __symbiotic_nondet_bool(void)
{
	_Bool x;
	klee_make_symbolic(&x, sizeof(x), "nondet-_Bool");
	return x;
}
