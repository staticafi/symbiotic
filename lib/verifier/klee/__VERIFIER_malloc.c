#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern void klee_make_symbolic(void *, size_t, const char *);

/* add our own versions of malloc and calloc */
/* non-deterministically return memory or NULL */
void *__VERIFIER_malloc(size_t size)
{
	_Bool fails;
	klee_make_symbolic(&fails, sizeof(fails), "malloc-fails");
	if (fails)
		return ((void *) 0);

	void *mem = malloc(size);
	klee_make_symbolic(mem, size, "malloc");

	return mem;
}
