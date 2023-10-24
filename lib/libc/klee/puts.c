extern int __symbiotic_nondet_int(void);
int puts(const char *s) {
    int ret =  __symbiotic_nondet_int();
    __VERIFIER_assume(ret >= -1);
    return ret;
}
