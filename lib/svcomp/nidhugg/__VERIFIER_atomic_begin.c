extern struct pthread_mutex_t;
extern pthread_mutex_t *__symbiotic_global_lock(void);
void __VERIFIER_atomic_begin(void)
{
	pthread_mutex_t *global_mutex = __symbiotic_global_lock();
	pthread_mutex_lock(global_mutex);
}
