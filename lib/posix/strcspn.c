#include "symbiotic-size_t.h"

size_t strcspn(const char *s, const char *reject)
{
	const char *it = s;
	while (*it) {
		/* check the intersection with accept */
		const char *a = reject;
		while (*a) {
			if (*a == *it) {
				return it - s;
			}
			++a;
		}

		++it;
	}

	return it - s;
}
