#include <stdint.h>

struct ldv_list_head {
 struct ldv_list_head *next, *prev;
};

struct ldv_list_head global_list_13 = { &(global_list_13), &(global_list_13) };

int main(void) {
 int *p = (int *)malloc(sizeof(int));
 global_list_13.next->prev = p;
 global_list_13.prev = &global_list_13;
}
