#include <stdio.h>
#include <errno.h>

extern _Bool __VERIFIER_nondet__Bool(void);
extern void klee_warning_once(const char *msg);

int fflush(FILE *stream) {
    klee_warning_once("overapproximating function model");
    if (__VERIFIER_nondet__Bool())
        return 0;
    errno = EBADF;
    return EOF;
}
