#include "symbiotic-size_t.h"

int strncmp(const char *s1, const char *s2, size_t n)
{
	size_t i;
	for (i = 0; i < n; ++i) {
		if (s1[i] != s2[i])
			return s1[i] < s2[i] ? -1 : 1;

		if (s1[i] == '\0' /* => s2[i] == '\0' */)
			return 0;
	}

	return 0;
}
