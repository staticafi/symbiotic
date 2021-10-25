#include <stdlib.h>

char *global;

int main(void) {
	global = (char *)malloc(sizeof(char));
	global = (char *)malloc(sizeof(char));
	free(global);
	return 0;
}
