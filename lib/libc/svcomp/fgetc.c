#include <stdio.h>
extern _Bool __VERIFIER_nondet__Bool(void);

extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

int fgetc(FILE *f) {
	// model failure
	if (__VERIFIER_nondet__Bool())
		return EOF;
	// otherwise we do not know how to do that properly...
	klee_warning_once("unsupported function model");
    	klee_silent_exit(1);
}
