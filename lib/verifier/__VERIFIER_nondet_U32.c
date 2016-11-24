unsigned int __VERIFIER_nondet_U32(void)
{
	unsigned int x;
	klee_make_symbolic(&x, sizeof(x), "nondet-u32");
	return x;
}
