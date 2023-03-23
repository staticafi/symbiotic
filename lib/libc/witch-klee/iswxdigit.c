#include <wctype.h>

extern int __VERIFIER_nondet_int(void);
extern void __VERIFIER_assume(int);


int iswxdigit( wint_t ch ) {

    int result = __VERIFIER_nondet_int();
    if ((ch >= 'a' && ch <= 'f') || (ch >= 'A' && ch <= 'F') || (ch >= '0' && ch <= '9'))
        __VERIFIER_assume(result > 0 || result < 0);
    else
        __VERIFIER_assume(result = 0);

    return result;


} 
