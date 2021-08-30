#include <stdio.h>
extern unsigned char __VERIFIER_nondet_uchar(void);
extern _Bool __VERIFIER_nondet__Bool(void);

int fgetc(FILE *f) {
	if (__VERIFIER_nondet__Bool())
		return EOF;
	return (int)__VERIFIER_nondet_uchar();
}
