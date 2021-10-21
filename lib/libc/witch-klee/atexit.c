#define MAX_ATEXIT 128

static void (*AtExit[MAX_ATEXIT])(void);
static unsigned NumAtExit;

void abort(void) __attribute__((noreturn));

static void RunAtExit(void) __attribute__((destructor));
static void RunAtExit(void) {
    unsigned i;

    for (i = NumAtExit; i > 0; --i) {
        AtExit[i-1]();
    }
}

int atexit(void (*fn)(void)) {
    if (NumAtExit == MAX_ATEXIT) {
        abort();
    }

    AtExit[NumAtExit] = fn;
    ++NumAtExit;

    return 0;
}
