// we do not want to inline the assert, it makes a mess in some cases
// (fixes jain_1_true-unreach-call.c with classical CD algorithm)
void __VERIFIER_assert(int) __attribute__((noinline, weak));
void __VERIFIER_error(void) __attribute__((noreturn));
void __VERIFIER_assert(int expr)
{
	if (!expr)
		__VERIFIER_error();
}
