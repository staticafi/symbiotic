unsigned short __VERIFIER_nondet_U16(void)
{
	static unsigned short x;
	klee_make_symbolic(&x, sizeof(x), "nondet-ushort");
	return x;
}
