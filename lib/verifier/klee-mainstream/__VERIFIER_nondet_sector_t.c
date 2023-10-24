#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

unsigned long __symbiotic_nondet_sector_t(void)
{
	unsigned long x;
	klee_make_symbolic(&x, sizeof(x), "nondet-sector_t");
	return x;
}
