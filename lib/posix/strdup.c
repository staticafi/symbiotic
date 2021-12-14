#include "symbiotic-size_t.h"

extern _Bool __symbiotic_nondet__Bool(void);
extern void *malloc(size_t);
extern void *memcpy(void *dest, const void *src, size_t n);
extern size_t strlen(const char*);

char *strdup(const char *str)
{
	size_t len = strlen(str) + 1;
	if (__symbiotic_nondet__Bool())
		return ((void *) 0);
	char *mem = malloc(len);//__VERIFIER_malloc(len);
	if (!mem)
		return ((void *) 0);

	memcpy(mem, str, len);
	return mem;
}
