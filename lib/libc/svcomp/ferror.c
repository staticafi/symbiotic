
extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

int ferror(void* f) {
	klee_warning_once("unsupported function model");
    	klee_silent_exit(1);
}


