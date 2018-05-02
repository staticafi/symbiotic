void __VERIFIER_error(void) __attribute__((noreturn));

// there is this bug in clang that removes
// functions that have the __inline attribute
__inline void error(void) {
	__VERIFIER_error();
}

int main(void) {
	error();
	return 0;
}
