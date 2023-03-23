extern int __VERIFIER_nondet_int(void);
extern void __VERIFIER_assume(int);

double sqrt (double __x) {
    double result = __VERIFIER_nondet_double();
    __VERIFIER_assume(result * result == __x);
    return result;
}
