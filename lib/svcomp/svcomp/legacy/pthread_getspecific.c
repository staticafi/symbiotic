#include <pthread.h>

__attribute__((noreturn))
void klee_report_error(const char *file, 
  		 int line, 
  		 const char *message, 
  		 const char *suffix);

void *pthread_getspecific(pthread_key_t key) {
    klee_report_error(__FILE__, __LINE__, "unsupported pthread API", "pthread");
}

