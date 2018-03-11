#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

void __VERIFIER_make_nondet(void *mem, size_t size, const char *name)
{
	if (size > 0)
		klee_make_symbolic(mem, size, name);
}
