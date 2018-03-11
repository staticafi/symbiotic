#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern _Bool __VERIFIER_nondet__Bool(void);
extern void __VERIFIER_assume(int);
extern void *memset(void *s, int c, size_t n);

void *__VERIFIER_calloc(size_t nmem, size_t size)
{
	_Bool fails = __VERIFIER_nondet__Bool();
	if (fails)
		return ((void *) 0);

	void *mem = malloc(nmem * size);
	__VERIFIER_assume(mem != (void *)0);
	memset(mem, 0, nmem * size);

	return mem;
}

