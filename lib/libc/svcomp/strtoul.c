
extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

unsigned long int strtoul(const char *nptr, char **endptr, int base) {
	(void)*nptr;
	if (endptr)
		(void)*endptr;
	// otherwise we do not know how to do that properly...
	klee_warning_once("unsupported function model");
    klee_silent_exit(1);
}
