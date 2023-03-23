#include <symbiotic-size_t.h>

typedef signed long int time_t;

extern void klee_make_symbolic(void *, size_t, const char *);
extern void klee_assume(unsigned long);

time_t time(time_t *tloc) {
	time_t ret;
	klee_make_symbolic(&ret, sizeof(ret), "nondet_time");
	klee_assume(ret >= -1);
	if (tloc)
		*tloc = ret;

	return ret;
}
