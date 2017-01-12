#include "symbiotic-size_t.h"

size_t strlen(const char *str)
{
	const char *it = str;
	while (*it)
		++it;

	return it - str;
}

