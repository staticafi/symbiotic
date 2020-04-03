#include <stdlib.h>

int main(void) {
	int *p = 0;
	if (p == 0) {
		*p = 3;
	}
	free(p);
}
