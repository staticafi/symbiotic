#include "symbiotic-size_t.h"

extern void *malloc(size_t);
extern void *memcpy(void *dest, const void *src, size_t n);

char *strdup(const char *str)
{
	size_t len = strlen(str);
	char *mem = malloc(len);
	if (!mem)
		return ((void *) 0);

	memcpy(mem, str, len);
	return mem;
}
