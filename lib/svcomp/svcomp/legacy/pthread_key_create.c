#include <pthread.h>

int pthread_key_create(pthread_key_t *key, void (*destructor)(void*)) {
    *key = 0;
    return 0;
}
