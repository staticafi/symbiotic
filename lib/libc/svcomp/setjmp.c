extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

int setjmp(int *env) {
	// otherwise we do not know how to do that properly...
	klee_warning_once("unsupported function model");
    	klee_silent_exit(1);
}
