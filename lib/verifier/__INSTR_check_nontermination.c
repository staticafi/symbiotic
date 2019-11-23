void __INSTR_fail(void) __attribute__((noreturn));
void __INSTR_check_nontermination(_Bool c) {
	if (c)
		__INSTR_fail();
}
