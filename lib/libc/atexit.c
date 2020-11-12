#define MAX_ATEXIT 128

static void (*AtExit[MAX_ATEXIT])(void);
static unsigned NumAtExit;

void klee_report_error(const char *, int, const char *, const char *);
static void RunAtExit(void) __attribute__((destructor));
static void RunAtExit(void) {
    unsigned i;

    for (i = NumAtExit - 1; i < MAX_ATEXIT; --i) AtExit[i]();
}

int atexit(void (*fn)(void)) {
    if (NumAtExit == MAX_ATEXIT) {
        klee_report_error(__FILE__, __LINE__, "atexit: no room in array!",
                          "exec");
    }

    AtExit[NumAtExit] = fn;
    ++NumAtExit;

    return 0;
}
