#include <pthread.h>

void *__symbiotic_global_lock(void) {
	static pthread_mutex_t global_lock = PTHREAD_MUTEX_INITIALIZER;
	return (void*)&global_lock;
}
