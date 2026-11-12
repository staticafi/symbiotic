#include "symbiotic-size_t.h"

/* wchar_t is a 32-bit int on the platforms of SV-COMP (ILP32 and LP64) */
int *wmemchr(const int *s, int c, size_t n)
{
	size_t i;
	for (i = 0; i < n; ++i)
		if (s[i] == c)
			return (int *) &s[i];

	return ((int *) 0);
}
