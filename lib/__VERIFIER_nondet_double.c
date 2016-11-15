double __VERIFIER_nondet_double(void)
{
	double x;
	klee_make_symbolic(&x, sizeof(x), "nondet-double");
	return x;
}
