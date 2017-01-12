#include "symbiotic-size_t.h"

size_t strspn(const char *s, const char *accept)
{
	const char *it = s;
	while (*it) {
		/* check the intersection with accept */
		const char *a = accept;
		_Bool found = 0;
		while (*a) {
			if (*a == *it) {
				found = 1;
				break;
			}
			++a;
		}

		if (!found)
			return it - s;

		++it;
	}

	return it - s;
}
