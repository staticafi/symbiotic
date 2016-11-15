unsigned short __VERIFIER_nondet_ushort(void)
{
	unsigned short x;
	klee_make_symbolic(&x, sizeof(x), "nondet-ushort");
	return x;
}
