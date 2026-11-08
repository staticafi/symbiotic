#include <stdarg.h>

extern int __symbiotic_nondet_int(void);

/*
 * Model of printf for the verification of memory safety.
 * It prints nothing, it only performs the memory accesses
 * that may be invalid in printf:
 *  - it reads the format string,
 *  - it reads the first character of every %s argument (this exposes
 *    dangling, freed or otherwise invalid pointers; we do not read the
 *    whole string as non-terminated strings are not considered errors
 *    in SV-COMP tasks and it would be expensive),
 *  - it writes to the argument of %n.
 * Other arguments are only consumed (with the right size, so that
 * the following arguments are read correctly).
 *
 * The returned value (and the value written by %n) is an arbitrary
 * integer. This is an overapproximation of the real behavior (printf
 * returns the number of printed characters or a negative value on error).
 */
int printf(const char *restrict format, ...)
{
    va_list ap;

    va_start(ap, format);
    for (const char *p = format; *p; ++p) {
        if (*p != '%')
            continue;

        /* skip flags, width, precision and length modifiers;
         * longs is 1 for l/z/t and 2 for ll/j/q/L */
        int longs = 0;
        for (++p; *p; ++p) {
            if (*p == '*')
                (void) va_arg(ap, int);
            else if (*p == 'l' || *p == 'z' || *p == 't')
                ++longs;
            else if (*p == 'j' || *p == 'q' || *p == 'L')
                longs = 2;
            else if (!((*p >= '0' && *p <= '9') || *p == '.' || *p == 'h' ||
                       *p == '-' || *p == '+' || *p == ' ' || *p == '#' ||
                       *p == '\''))
                break;
        }

        if (!*p)
            break;

        switch (*p) {
        case '%':
            break;
        case 's': {
            const char *s = va_arg(ap, const char *);
            if (s) /* glibc prints "(null)" for NULL */
                (void) *(const volatile char *) s;
            break;
        }
        case 'n':
            *va_arg(ap, int *) = __symbiotic_nondet_int();
            break;
        case 'p':
            (void) va_arg(ap, void *);
            break;
        case 'f': case 'F': case 'e': case 'E':
        case 'g': case 'G': case 'a': case 'A':
            if (longs >= 2)
                (void) va_arg(ap, long double);
            else
                (void) va_arg(ap, double);
            break;
        default: /* integer conversions and %c */
            if (longs >= 2)
                (void) va_arg(ap, long long);
            else if (longs == 1)
                (void) va_arg(ap, long);
            else
                (void) va_arg(ap, int);
        }
    }
    va_end(ap);

    return __symbiotic_nondet_int();
}
