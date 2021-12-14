#include "symbiotic-size_t.h"

void klee_make_symbolic(void *, size_t, const char *);
extern void __VERIFIER_assume(int);
extern _Bool __symbiotic_nondet__Bool(void);
extern char __symbiotic_nondet_char(void);
extern unsigned __symbiotic_nondet_uint(void);

static char dummy_env[20];

char *getenv(const char *name) {
	(void) name;

	if (__symbiotic_nondet__Bool())
		return ((char *) 0);

	unsigned int idx = __symbiotic_nondet_uint();
	__VERIFIER_assume(idx < sizeof(dummy_env));

	for (unsigned int i = 0; i < idx; ++i) {
		dummy_env[i] = __symbiotic_nondet_char();
	}
	dummy_env[idx] = '\0';

	return dummy_env;
}
