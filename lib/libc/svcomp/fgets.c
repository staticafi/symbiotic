#include <stdio.h>
extern _Bool __symbiotic_nondet__Bool(void);
extern char __symbiotic_nondet_char(void);

extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

char* fgets(char* str, int count, FILE *f) {
    if (count <= 1)
        return NULL;

    if (__symbiotic_nondet__Bool())
        return NULL;

    size_t i;
    for (i = 0; i < count - 1; i++) {

        if (__symbiotic_nondet__Bool()) {
            str[i] = '\n';
            i++;
            break;
        }

        if (__symbiotic_nondet__Bool())
            break;

        str[i] = __symbiotic_nondet_char();
    }
    str[i] = 0;
    return str;
}
