float __VERIFIER_nondet_float(void)
{
	float x;
	klee_make_symbolic(&x, sizeof(x), "nondet-float");
	return x;
}
