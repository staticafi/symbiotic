unsigned long __VERIFIER_nondet_ulong(void)
{
	unsigned long x;
	klee_make_symbolic(&x, sizeof(x), "nondet-ulong");
	return x;
}
