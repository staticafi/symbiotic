// GPLv2

#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern void klee_make_symbolic(void *, size_t, const char *);
extern void *memset(void *s, int c, size_t n);

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

