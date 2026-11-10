#include "symbiotic-size_t.h"

extern void *realloc(void *, size_t);
extern _Bool __symbiotic_nondet__Bool(void);

/* non-deterministically fail: return NULL and leave the original
 * memory untouched (this is how a failing realloc behaves) */
void *__VERIFIER_realloc(void *ptr, size_t size)
{
	if (__symbiotic_nondet__Bool())
		return ((void *) 0);

	return realloc(ptr, size);
}
