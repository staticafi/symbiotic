extern void __VERIFIER_error() __attribute__ ((__noreturn__));
extern void __VERIFIER_assume();
void __VERIFIER_assert(int cond) {
  if (!(cond)) {
    ERROR: __VERIFIER_error();
  }
  return;
}
int __VERIFIER_nondet_int();

int main() {
    int x=__VERIFIER_nondet_int();
    int y=__VERIFIER_nondet_int();

    __VERIFIER_assume(x > 0);
    __VERIFIER_assume(y <= 1);

    if (y > 0) {
        while(x<2) {
                x=x+y;
        }
    }
    __VERIFIER_assert(y <= 0 || (y > 0 && x>=2));
    return 0;
}
