#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

void *__symbiotic_nondet_pointer(void)
{
	void *x;
	klee_make_symbolic(&x, sizeof(void *), "void*");
	return x;
}
