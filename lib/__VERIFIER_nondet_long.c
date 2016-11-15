long __VERIFIER_nondet_long(void)
{
	long x;
	klee_make_symbolic(&x, sizeof(x), "nondet-long");
	return x;
}
