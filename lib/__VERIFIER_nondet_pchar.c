char *__VERIFIER_nondet_pchar()
{
	char *x;
	klee_make_symbolic(&x, sizeof(void *), "char*");
	return x;
}
