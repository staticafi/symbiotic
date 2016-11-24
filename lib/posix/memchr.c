#include "symbiotic-size_t.h"

void *memchr(const void *mem, int c, size_t n)
{
	int i;
	unsigned char *byte = mem;
	for (i = 0; i < n; ++i)
		if (byte[i] == (unsigned char) c)
			return (void *) byte;

	return ((void *) 0);
}
