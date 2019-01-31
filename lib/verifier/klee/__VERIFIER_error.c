extern void __assert_fail (__const char *__assertion, __const char *__file,
			   unsigned int __line, __const char *__function) __attribute__((noreturn));

void __VERIFIER_error(void) __attribute__((noreturn,noinline));
void __VERIFIER_error(void)
{
	/* FILE and LINE will be wrong, but that doesn't matter, klee will
	   replace this call by its own handler anyway */
	__assert_fail("verifier assertion failed", __FILE__, __LINE__, __func__);
}
