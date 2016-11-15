short __VERIFIER_nondet_short(void)
{
	short x;
	klee_make_symbolic(&x, sizeof(x), "nondet-short");
	return x;
}
