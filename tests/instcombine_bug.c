#include <assert.h>
int __VERIFIER_nondet_int();

void klee_make_symbolic(void *, unsigned long size, const char *); 
int main(void)
{
  int n,l;
  klee_make_symbolic(&n, sizeof n, "n");
  if (!(1 <= n && n <= 1000000))
        return 0;

  l = n/2 + 1;

  if(l>1) {
    l--;
  }
  assert(l != 0); 

  return 0;
}
