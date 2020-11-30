extern void klee_warning_once(const char *);
void klee_silent_exit(int) __attribute__((noreturn));

unsigned long strtoul(const char *nptr, char **endptr, int base)
{
    *nptr;
    if (endptr)
        *endptr;
	klee_warning_once("unsupported function model");
    klee_silent_exit(1);
}
