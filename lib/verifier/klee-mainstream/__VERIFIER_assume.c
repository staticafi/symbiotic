extern void klee_assume(int);

void __VERIFIER_assume(int expr)
{
	klee_assume(expr);
}
