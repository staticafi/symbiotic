#include <pthread.h>
#include <errno.h>

#include "symbiotic-barrier.h"

/*
 * The model of barriers is exact only for single-threaded programs, see
 * symbiotic-barrier.h. Symbiotic does not link it into programs that create
 * threads.
 */
int pthread_barrier_init(pthread_barrier_t *barrier,
                         const pthread_barrierattr_t *attr,
                         unsigned count)
{
	(void) attr;
	if (count == 0)
		return EINVAL;

	struct __symbiotic_barrier *b = (struct __symbiotic_barrier *) barrier;
	b->count = count;
	b->arrived = 0;
	return 0;
}
