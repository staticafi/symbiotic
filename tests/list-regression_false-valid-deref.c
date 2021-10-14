extern void __VERIFIER_error() __attribute__ ((__noreturn__));

struct list {
 int n;
 struct list *next;
};


int i = 1;

struct list* append(struct list *l, int n)
{
 struct list *new_el;

 // bug: wrong sizeof
 new_el = malloc(sizeof(struct list*));

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

 if (l->next->next->n == 0);
   __VERIFIER_error();
 return 0;
}
