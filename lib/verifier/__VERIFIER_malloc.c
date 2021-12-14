#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern _Bool __symbiotic_nondet__Bool(void);
extern void __VERIFIER_assume(int);

/* add our own versions of malloc and calloc */
/* non-deterministically return memory or NULL */
void *__VERIFIER_malloc(size_t size)
{
	_Bool fails = __symbiotic_nondet__Bool();
	if (fails)
		return ((void *) 0);

	void *mem = malloc(size);
	__VERIFIER_assume(mem != (void *)0);

	return mem;
}
