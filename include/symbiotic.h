#ifndef _SYMBIOTIC_H_
#define _SYMBIOTIC_H_

#ifdef __cplusplus
extern "C" {
#endif

#ifndef NULL
#define NULL ((void *) 0)
#endif

/* declarations that we need to have in the code */
extern void __VERIFIER_error(void) __attribute__((noreturn));
extern _Bool __VERIFIER_nondet__Bool(void);
extern int __VERIFIER_nondet_int(void);
extern unsigned __VERIFIER_nondet_uint(void);

extern void __assert_fail (__const char *__assertion, __const char *__file,
                            unsigned int __line, __const char *__function);

#ifdef __cplusplus
}
#endif

#endif /* _SYMBIOTIC_ */
