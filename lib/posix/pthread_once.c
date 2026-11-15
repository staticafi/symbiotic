#include <pthread.h>

/*
 * Run init_routine on the first call with the given once_control only
 * (PTHREAD_ONCE_INIT is 0). Without a model, the verifiers treat
 * pthread_once as a pure function and init_routine is never called.
 *
 * The flag is set before calling init_routine, so a recursive call from
 * init_routine returns instead of deadlocking as in glibc. With several
 * threads, two calls may interleave and both run init_routine, and a call
 * does not wait for an init_routine running in another thread. Both only
 * add executions, so no error is missed.
 */
int pthread_once(pthread_once_t *once_control, void (*init_routine)(void))
{
	if (*once_control == 0) {
		*once_control = 1;
		init_routine();
	}
	return 0;
}
