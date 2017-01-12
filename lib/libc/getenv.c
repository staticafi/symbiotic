#include "symbiotic-size_t.h"

void klee_make_symbolic(void *, size_t, const char *);
void __VERIFIER_assume(int);

static char dummy_env[20];

char *getenv(const char *name) {
	if (__VERIFIER_nondet__Bool())
		return ((char *) 0);

	unsigned int idx = __VERIFIER_nondet_uint();
	__VERIFIER_assume(idx < sizeof(dummy_env));
	dummy_env[idx] = '\0';

	if (idx > 0)
		klee_make_symbolic(dummy_env, idx + 1, "dummy_env");

	return dummy_env;
}
