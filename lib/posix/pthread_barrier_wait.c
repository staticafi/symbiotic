#include <pthread.h>

#include "symbiotic-barrier.h"

extern void __VERIFIER_assume(int);

/*
 * The model of barriers is exact only for single-threaded programs, see
 * symbiotic-barrier.h. Symbiotic does not link it into programs that create
 * threads.
 */
int pthread_barrier_wait(pthread_barrier_t *barrier)
{
	struct __symbiotic_barrier *b = (struct __symbiotic_barrier *) barrier;
	if (++b->arrived < b->count) {
		/* no other thread can arrive, the caller waits forever */
		__VERIFIER_assume(0);
	}

	/* the barrier is reset and can be used again */
	b->arrived = 0;
	return PTHREAD_BARRIER_SERIAL_THREAD;
}
