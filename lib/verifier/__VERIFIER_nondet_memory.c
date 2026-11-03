#include <stddef.h>
extern unsigned char __symbiotic_nondet_uchar();

void __VERIFIER_nondet_memory(void *mem, size_t size) {
    unsigned char *p = mem;
    for (size_t i = 0; i < size; i++) {
        p[i] = __symbiotic_nondet_uchar();
    }
}
