extern void klee_silent_exit(int) __attribute__((noreturn));
void __VERIFIER_silent_exit(int status) __attribute__((noreturn,noinline));
void __VERIFIER_silent_exit(int status) {
	klee_silent_exit(0);
}
