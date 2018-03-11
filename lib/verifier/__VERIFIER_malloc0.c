#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern void __VERIFIER_assume(int);

/* this versions never return NULL */
void *__VERIFIER_malloc0(size_t size)
{
	void *mem = malloc(size);
	__VERIFIER_assume(mem != (void *)0);
	return mem;
}

