#include "symbiotic-size_t.h"

extern void klee_make_symbolic(void *, size_t, const char *);

char __symbiotic_nondet_char_named(const char *name)
{
	char x;
	klee_make_symbolic(&x, sizeof(x), name);
	return x;
}
