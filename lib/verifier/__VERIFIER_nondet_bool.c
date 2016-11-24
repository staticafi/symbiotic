_Bool __VERIFIER_nondet_bool(void)
{
	_Bool x;
	klee_make_symbolic(&x, sizeof(x), "nondet-_Bool");
	return x;
}
