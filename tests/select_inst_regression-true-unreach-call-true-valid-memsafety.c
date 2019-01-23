#include <assert.h>

int a = 0;
int *p = ((void *) 0); 

void set(void)
{
        if (!a)
                p = &a; 
        else
                p = ((void *) 0); 
}

int main(void)
{
        int b = 2;
        if (a > b) {
                set();
                *p = 3;
        } else {
                set();
                *p = 4;
        }

        assert(a == 4); 
        return 0;
}
