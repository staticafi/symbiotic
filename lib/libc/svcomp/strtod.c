#include <errno.h>

extern double __VERIFIER_nondet_double(void);
extern int __VERIFIER_nondet_int(void);
extern void klee_warning_once(const char *);

double strtod(const char *str, char **endptr) {
	(void)str;
	klee_warning_once("overapproximating function model");
	if (endptr) // check the dereference
		*endptr = str;
	errno = __VERIFIER_nondet_int();
	return __VERIFIER_nondet_double();
}

