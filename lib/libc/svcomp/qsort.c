// our implementation of qsort does not actually sorts,
// but just checks that the array is sorted -- so that if
// the array is symbolic, we can continue with this assumption.
// If the array is concrete and unsorted, we abort...
//
#include "symbiotic-size_t.h"

extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

void qsort(void *base, size_t nmemb, size_t size,
           int (*compar)(const void *, const void *)) {
    unsigned char *nxt = (unsigned char *) base;
    for (unsigned i = 1; i < nmemb; ++i) {
        nxt += size;
        if (compar(base, nxt) > 0) { /* unsorted */
	        klee_warning_once("unsorted array in qsort, aborting path");
    	    klee_silent_exit(1);
        }
        base = (void *)nxt;
    }
}
