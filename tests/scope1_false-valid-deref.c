#include <stdlib.h>

int main(void) {
	int *p;
	for (int i = 0; i < 10; ++i)
		p = &i;

	*p = 3;

	return 0;
}
