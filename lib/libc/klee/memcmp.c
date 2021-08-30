#include "symbiotic-size_t.h"

#define BYTE(mem, i) (((unsigned char *) mem)[(i)])

int memcmp(const void *dest, const void *src, size_t n)
{
	size_t i = 0;
	while(i < n && BYTE(dest, i) == BYTE(src, i))
		++i;

	return ((i == n) ? 0 : ((BYTE(dest, i) < BYTE(src, i)) ? -1 : 1));
}

