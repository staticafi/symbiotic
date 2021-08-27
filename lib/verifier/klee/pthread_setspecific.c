#include <pthread.h>

__attribute__((noreturn))
void klee_report_error(const char *file, 
  		 int line, 
  		 const char *message, 
  		 const char *suffix);


int pthread_setspecific(pthread_key_t key, const void *value) {
    klee_report_error(__FILE__, __LINE__, "unsupported pthread API", "pthread");
}

