#include "symbiotic-size_t.h"

void *__kmalloc(size_t size)
{
	extern void *malloc(size_t);
	return malloc(size);
}
