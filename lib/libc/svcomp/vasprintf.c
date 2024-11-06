#include "symbiotic-size_t.h"
#include <stdarg.h>

extern int vsprintf( char* restrict buffer, const char* restrict format, va_list vlist );
extern int vsnprintf( char* restrict buffer, size_t bufsz, const char* restrict format, va_list vlist );

int vasprintf( char **restrict strp, const char *restrict format, va_list vlist )
{
    const int sz = vsnprintf(0, 0, format, vlist);
    *strp = malloc((sz+1)*sizeof(char));
    vsprintf(*strp, format, vlist);
    return sz;
}

