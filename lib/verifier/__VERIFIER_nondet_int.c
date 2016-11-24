int __VERIFIER_nondet_int(void)
{
	int x;
	klee_make_symbolic(&x, sizeof(x), "nondet-int");
	return x;
}
