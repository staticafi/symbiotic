#include <pthread.h>

extern void *__symbiotic_global_lock(void);
void __VERIFIER_atomic_end(void)
{
	pthread_mutex_unlock(__symbiotic_global_lock());
}
