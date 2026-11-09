#include <stdio.h>
extern _Bool __symbiotic_nondet__Bool(void);
extern unsigned char __symbiotic_nondet_uchar(void);

int fgetc(FILE *f) {
	// model failure
	if (__symbiotic_nondet__Bool())
		return EOF;
	return (int)__symbiotic_nondet_uchar();
}
