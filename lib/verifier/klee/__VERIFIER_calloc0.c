// GPLv2

#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern void *memset(void *s, int c, size_t n);
extern void klee_make_symbolic(void *, size_t, const char *);

void *__VERIFIER_calloc0(size_t nmem, size_t size)
{
	void *mem = malloc(nmem * size);
	//klee_assume(mem != (void *) 0);
	klee_make_symbolic(mem, nmem * size, "calloc");
	memset(mem, 0, nmem * size);

	return mem;
}

