extern void __ikos_assert(int);

void __VERIFIER_error(void) __attribute__((noreturn,noinline));
void abort(void) __attribute__((noreturn));
void __VERIFIER_error(void)
{
	__ikos_assert(0);
	abort();
}
