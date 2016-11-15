#include "symbiotic-size_t.h"

void *kzalloc(int size, int gfp)
{
	(void) gfp;
	extern void *malloc(size_t size);
	return malloc(size);
}
