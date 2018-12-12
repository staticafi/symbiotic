#include <pthread.h>

pthread_mutex_t *__symbiotic_global_lock(void) {
	static pthread_mutex_t global_lock = PTHREAD_MUTEX_INITIALIZER;
	return &global_lock;
}
