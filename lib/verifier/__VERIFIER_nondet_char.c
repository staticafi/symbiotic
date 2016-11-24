char __VERIFIER_nondet_char(void)
{
	char x;
	klee_make_symbolic(&x, sizeof(x), "nondet-char");
	return x;
}
