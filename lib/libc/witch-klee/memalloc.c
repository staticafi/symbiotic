// GPLv2

#include "symbiotic-size_t.h"

extern void *malloc(size_t);
void klee_make_symbolic(void *, size_t, const char *);

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

void *memset(void *s, int c, size_t n);
void *__VERIFIER_calloc(size_t nmem, size_t size)
{
	_Bool fails;
	klee_make_symbolic(&fails, sizeof(fails), "calloc-fails");
	if (fails)
		return ((void *) 0);

	void *mem = malloc(nmem * size);
	/* do it symbolic, so that subsequent
	 * uses will be symbolic, but initialize it
	 * to 0s */
	klee_make_symbolic(mem, nmem * size, "calloc");
	memset(mem, 0, nmem * size);

	return mem;
}

/* this versions never return NULL */
void *__VERIFIER_malloc0(size_t size)
{
	void *mem = malloc(size);
	// NOTE: klee already assumes that
	//klee_assume(mem != (void *) 0);
	klee_make_symbolic(mem, size, "malloc0");

	return mem;
}

void *__VERIFIER_calloc0(size_t nmem, size_t size)
{
	void *mem = malloc(nmem * size);
	//klee_assume(mem != (void *) 0);
	klee_make_symbolic(mem, nmem * size, "calloc0");
	memset(mem, 0, nmem * size);

	return mem;
}

