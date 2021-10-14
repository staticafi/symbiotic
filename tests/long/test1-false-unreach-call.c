#include <assert.h>
#define N 10

extern int __VERIFIER_nondet_int(void);

int main( ) {
  int a[N];
  for (int i = 0; i < N; ++i) {
	  a[i] = __VERIFIER_nondet_int();
  }

  int swapped = 1;
  while (swapped) {
    swapped = 0;
    for (int i = 1; i < N; ++i) {
      if ( a[i - 1] < a[i] ) {
        int t = a[i];
        a[i] = a[i - 1];
        a[i-1] = t;
        swapped = 1;
      }
    }
  }

  for (int x = 0 ; x < N ; x++ ) {
    for (int y = x+1 ; y < N ; y++ ) {
      assert(a[x] <= a[y]);
    }
  }
  return 0;
}
