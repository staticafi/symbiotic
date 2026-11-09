#include "symbiotic-size_t.h"

size_t strcspn(const char *s, const char *reject)
{
	const char *it = s;
	while (*it) {
		/* check the intersection with reject */
		const char *a = reject;
		_Bool found = 0;
		while (*a) {
			if (*a == *it) {
				found = 1;
				break;
			}
			++a;
		}

		if (found)
			return it - s;

		++it;
	}

	return it - s;
}
