#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

unsigned char __symbiotic_nondet_uchar_named(const char *name)
{
	unsigned char x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
