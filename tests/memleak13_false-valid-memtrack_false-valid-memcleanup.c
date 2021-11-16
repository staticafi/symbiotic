#include <stdlib.h>

struct ldv_list_head {
  struct ldv_list_head *next, *prev;
};

 struct ldv_list_head global_list_13 = { &(global_list_13), &(global_list_13) };
 struct A13 {
  int data;
  struct ldv_list_head list;
};
void foo() {
    struct A13 *p = (struct A13 *)malloc(sizeof(struct A13));
    global_list_13.prev = &p->list;
}
int main(void) {
    foo();
    global_list_13.prev = &global_list_13;
}
