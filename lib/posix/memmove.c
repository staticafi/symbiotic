#include "symbiotic-size_t.h"

void *memcpy(void *dest, const void *src, size_t n);

void *memmove(void *dest, const void *src, size_t n) {
	void *tmp = malloc(n);
	memcpy(tmp, src, n);
	memcpy(dest, tmp, n);
	free(tmp);
	return dest;
}
