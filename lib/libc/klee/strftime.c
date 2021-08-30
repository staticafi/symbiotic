#include <time.h>

extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

size_t strftime(char *restrict s, size_t n, const char *restrict f, const struct tm *restrict tm)
{
	*s;
	*f;
	*tm;
	klee_warning_once("unsupported function model");
    	klee_silent_exit(1);
}
