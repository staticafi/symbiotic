#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern void klee_make_symbolic(void *, size_t, const char *);

/* this versions never return NULL */
void *__VERIFIER_malloc0(size_t size)
{
	void *mem = malloc(size);
	// NOTE: klee already assumes that
	//klee_assume(mem != (void *) 0);
	if (size > 0)
		klee_make_symbolic(mem, size, "malloc");

	return mem;
}

