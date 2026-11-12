#include "symbiotic-size_t.h"

extern char __symbiotic_nondet_char();
extern _Bool __symbiotic_nondet__Bool();

/*
 * Model of recv: it fails (returns -1, errno is not modelled) or receives
 * an arbitrary number of arbitrary bytes, but at most len of them.
 * Without the model, recv returned an unconstrained value (e.g., larger
 * than len) and the programs that use it as an index into the buffer
 * (e.g., inputBuffer[recvResult] = '\0' in Juliet) went out of bounds.
 */
long recv(int sockfd, void *buf, size_t len, int flags)
{
    (void) sockfd;
    (void) flags;

    if (__symbiotic_nondet__Bool())
        return -1;

    size_t i;
    for (i = 0; i < len; ++i) {
        if (__symbiotic_nondet__Bool())
            break;
        ((char *) buf)[i] = __symbiotic_nondet_char();
    }
    return (long) i;
}
