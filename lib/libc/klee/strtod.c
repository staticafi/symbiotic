extern double __VERIFIER_nondet_double(void);
extern void klee_warning(const char *);
double strtod(const char *str, char **endptr) {
	(void)str;
	klee_warning("unsupported function model");
	if (endptr) // check the dereference
		*endptr = str;
	return __VERIFIER_nondet_double();
}

