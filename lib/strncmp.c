#include "symbiotic-size_t.h"

int strncmp(const char *s1, const char *s2, size_t n)
{
	while(*s1 == *s2) {
		if (*s1 == '\0' /* => *s2 == '\0' */)
			return 0;
		++s1;
		++s2;

		if (--n == 0)
			return 0;
	}

	return ((*s1 < *s2) ? -1 : 1);
}
