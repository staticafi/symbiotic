#include "symbiotic-size_t.h"

extern void *memset(void *, int, size_t);

void *__memset(void *ptr, int c, size_t size)
{
	return memset(ptr, c, size);
}
