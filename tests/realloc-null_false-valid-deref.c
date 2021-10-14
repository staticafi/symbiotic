#include <stdlib.h>

int main(void)
{
    // should behave as malloc(0), which returns
    // either NULL or an object that cannot be dereferenced
    char *ptr = realloc(NULL, 0);
    if (ptr == NULL)
        return EXIT_SUCCESS;

    *ptr = (_Bool)1;
    free(ptr);
}
