
#include "symbiotic-size_t.h"

extern void *malloc(size_t);

/* this versions never return NULL */
void *__VERIFIER_malloc0(size_t size)
{
	void *mem = malloc(size);
	// NOTE: klee already assumes that
	//klee_assume(mem != (void *) 0);
	klee_make_symbolic(mem, size, "malloc0");

	return mem;
}

