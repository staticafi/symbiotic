#include "symbiotic-size_t.h"

void *memrchr(const void *mem, int c, size_t n)
{
	int i;
	const unsigned char *byte = mem;
	for (i = n - 1; i >= 0; --i)
		if (byte[i] == (unsigned char) c)
			return (void *) byte;

	return ((void *) 0);
}
