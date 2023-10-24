#include <stdio.h>
extern unsigned char __symbiotic_nondet_uchar(void);
extern _Bool __symbiotic_nondet__Bool(void);

int fgetc(FILE *f) {
	if (__symbiotic_nondet__Bool())
		return EOF;
	return (int)__symbiotic_nondet_uchar();
}
