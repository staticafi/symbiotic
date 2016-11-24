#include "symbiotic-size_t.h"

void *kzalloc(int size, int flgs)
{
	(void) flgs;
	extern void *malloc(size_t size);
	void *mem = malloc(size);
	memset(mem, 0, size);

	return mem;
}
