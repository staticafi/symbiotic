/* The assertion in main fails only after the thread wrote x: CSeq's lazy
   sequentialization must schedule the thread before main's check. */
typedef unsigned long pthread_t;
extern int pthread_create(pthread_t *, const void *, void *(*)(void *), void *);
extern int pthread_join(pthread_t, void **);
extern void abort(void);
extern void __assert_fail(const char *, const char *, unsigned int, const char *);
void reach_error() { __assert_fail("0", "thread_write_false-unreach-call.c", 9, "reach_error"); }

int x = 0;

void *thread(void *arg) {
    x = 1;
    return 0;
}

int main() {
    pthread_t t;
    pthread_create(&t, 0, thread, 0);
    if (x == 1)
        reach_error();
    pthread_join(t, 0);
    return 0;
}
