#include <pthread.h>

int pthread_barrier_destroy(pthread_barrier_t *barrier)
{
	(void) barrier;
	return 0;
}
