#ifndef SYMBIOTIC_BARRIER_H
#define SYMBIOTIC_BARRIER_H

/*
 * The state of a barrier, stored in the pthread_barrier_t object
 * (glibc's pthread_barrier_t has at least 20 bytes).
 *
 * The model is exact only for single-threaded programs: a thread that waits
 * at a barrier waits forever unless 'count' threads have arrived, i.e.,
 * unless count == 1. With several threads, blocking would cut off the
 * executions in which the other threads arrive later, so Symbiotic does not
 * link the model into programs that create threads (the calls then return
 * immediately, which only adds executions).
 */
struct __symbiotic_barrier {
	unsigned count;
	unsigned arrived;
};

_Static_assert(sizeof(struct __symbiotic_barrier) <= sizeof(pthread_barrier_t),
               "pthread_barrier_t too small for the model");

#endif
