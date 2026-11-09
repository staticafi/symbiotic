#include "symbiotic-size_t.h"
#include <stdio.h>

extern char __symbiotic_nondet_char();
extern _Bool __symbiotic_nondet__Bool();


size_t fread(void * buf, size_t size, size_t count, FILE * fp)
{
    if ((count == 0) || (size == 0))
        return (0);
    for (size_t i = 0; i < count * size; i++) {
        if (__symbiotic_nondet__Bool())
            return i / size;
        ((char*)buf)[i] = __symbiotic_nondet_char();
    }
    return count;
}
