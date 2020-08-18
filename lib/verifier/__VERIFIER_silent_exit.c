extern void __VERIFIER_assume(int);
void abort(void) __attribute__((noreturn));
void __VERIFIER_silent_exit(int status) __attribute__((noreturn,noinline));
void __VERIFIER_silent_exit(int status) {
	(void) status;
	__VERIFIER_assume(0);
	abort();
}
