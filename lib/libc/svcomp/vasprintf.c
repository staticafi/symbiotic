#include "symbiotic-size_t.h"
#include <stdarg.h>

extern int vsprintf( char* restrict buffer, const char* restrict format, va_list vlist );
extern int vsnprintf( char* restrict buffer, size_t bufsz, const char* restrict format, va_list vlist );

int vasprintf( char **restrict strp, const char *restrict format, va_list vlist )
{
    const int sz = vsnprintf(0, 0, format, vlist);
    if (sz < 0)
        return -1;

    /* like glibc: on allocation failure return -1 and do not report success */
    char *buf = malloc((sz+1)*sizeof(char));
    if (!buf)
        return -1;

    vsprintf(buf, format, vlist);
    *strp = buf;
    return sz;
}

