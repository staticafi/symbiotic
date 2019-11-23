extern void __assert_fail (__const char *__assertion, __const char *__file,
			   unsigned int __line, __const char *__function) __attribute__((noreturn));

void __INSTR_fail(void) __attribute__((noreturn));
void __INSTR_fail(void) {
	__assert_fail("0 && infinite loop", __FILE__, __LINE__, __func__);
}

