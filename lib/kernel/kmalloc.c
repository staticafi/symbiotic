#include "symbiotic-size_t.h"

extern void *malloc(size_t);

void *kmalloc(size_t size, unsigned flags)
{
	(void) flags;
	return malloc(size);
}
