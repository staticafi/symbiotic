extern void __VERIFIER_error() __attribute__ ((__noreturn__));
void __VERIFIER_assert(int);

typedef unsigned int size_t;
extern  __attribute__((__nothrow__)) void *malloc(size_t __size ) __attribute__((__malloc__));


struct list {
 int n;
 struct list *next;
};



int i = 1;

struct list* append(struct list *l, int n)
{
 struct list *new_el;

 new_el = malloc(8);

 new_el->n = n;
 new_el->next = l;

 return new_el;
}

int main(void)
{
 struct list *l,m;
 l = &m;
 l->next = 0;
 l->n = 0;

 l = append(l, 1);
 l = append(l, 2);

 __VERIFIER_assert(l->next->next->n != 0);
 return 0;
}
