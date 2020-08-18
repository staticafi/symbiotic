#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern void *memset(void *, int, size_t);

void *kzalloc(int size, int flgs)
{
	(void) flgs;
	void *mem = malloc(size);
	memset(mem, 0, size);

	return mem;
}
