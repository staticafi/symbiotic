#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern _Bool __VERIFIER_nondet__Bool(void);
extern void klee_make_nondet(void *, size_t, const char *, int);
extern void *memset(void *s, int c, size_t n);

void *__VERIFIER_calloc(size_t nmem, size_t size)
{
	if (__VERIFIER_nondet__Bool())
		return ((void *) 0);

	void *mem = malloc(nmem * size);
	/* do it symbolic, so that subsequent
	 * uses will be symbolic, but initialize it
	 * to 0s */
	klee_make_nondet(mem, nmem * size, "--:calloc0:", id);
	memset(mem, 0, nmem * size);

	return mem;
}

