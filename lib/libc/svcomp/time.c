#include <symbiotic-size_t.h>

typedef signed long int time_t;

extern void abort(void) __attribute__((__noreturn__));
extern long int __symbiotic_nondet_long(void);

time_t time(time_t *tloc) {
    time_t ret = __symbiotic_nondet_long();
    if (ret < -1)
	abort();
    if (tloc)
        *tloc = ret;

    return ret;
}
