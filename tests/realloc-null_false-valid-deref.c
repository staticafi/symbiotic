#include <stdlib.h>

int main(void)
{
    char *ptr = malloc(0);
    //char *ptr = realloc(NULL, 0);
    if (ptr == NULL)
        return EXIT_SUCCESS;

    (void) *ptr;
    free(ptr);
}
