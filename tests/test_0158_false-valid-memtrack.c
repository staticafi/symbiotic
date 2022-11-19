#include <stdlib.h>

extern int __VERIFIER_nondet_int(void);

int main()
{
    union {
        void *p0;

        struct {
            char c[2];
            int  p1;
            int  p2;
        } str;

    } data;

    // alloc 37B on heap
    data.p0 = malloc(37U);
    // this introduces a memleak
    data.str.c[1] = sizeof data.str.p1;

    return 0;
}
