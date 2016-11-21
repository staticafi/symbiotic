#include "symbiotic-size_t.h"

void *kzalloc(int size, int)
{
	extern void *malloc(size_t size);
	void *mem = malloc(size);
	memset(mem, 0, size);
	return mem;
}
