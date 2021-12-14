#include <errno.h>

/** extern double __symbiotic_nondet_double(void); */
/** extern int __symbiotic_nondet_int(void);       */
extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

double strtod(const char *str, char **endptr) {
	klee_warning_once("unsupported function model");
    klee_silent_exit(1);
    // klee_warning_once("overapproximating function model");
    // (void)str;
    // if (endptr) // check the dereference
    // 	*endptr = str;
    // errno = __symbiotic_nondet_int();
    // return __symbiotic_nondet_double();
}

