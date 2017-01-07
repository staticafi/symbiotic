//extern void exit(int);
extern void abort(void) __attribute__((noreturn));
void __VERIFIER_exit(int status) __attribute__((noinline));
void __VERIFIER_exit(int status) {
//	exit(status);
	abort();
}
