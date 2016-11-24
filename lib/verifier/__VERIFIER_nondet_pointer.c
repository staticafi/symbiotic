void *__VERIFIER_nondet_pointer()
{
	void *x;
	klee_make_symbolic(&x, sizeof(void *), "void*");
	return x;
}
