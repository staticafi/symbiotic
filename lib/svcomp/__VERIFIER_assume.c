extern void abort(void) __attribute__((noreturn));
void __VERIFIER_assume(int expr)
{
	if (!expr)
		abort();
}
