extern void __assert_fail (__const char *__assertion, __const char *__file,
			   unsigned int __line, __const char *__function);

// we do not want to inline the assert, it makes a mess in some cases
// (fixes jain_1_true-unreach-call.c with classical CD algorithm)
void __VERIFIER_assert(int) __attribute__((noinline, weak));
void __VERIFIER_assert(int expr)
{
	if (!expr)
		__assert_fail("verifier assertion failed", __FILE__, __LINE__, __func__);
}
