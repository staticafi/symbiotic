#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern _Bool __VERIFIER_nondet__Bool(void);
extern void klee_make_nondet(void *, size_t, const char *, int);

/* add our own versions of malloc and calloc */
/* non-deterministically return memory or NULL */
void *__VERIFIER_malloc(size_t size, int id)
{
	if (__VERIFIER_nondet__Bool())
		return ((void *) 0);

	void *mem = malloc(size);
	klee_make_nondet(mem, size, "--:malloc:", id);

	return mem;
}
