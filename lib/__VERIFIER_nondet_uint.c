unsigned int __VERIFIER_nondet_uint(void)
{
	unsigned int x;
	klee_make_symbolic(&x, sizeof(x), "nondet-uint");
	return x;
}
