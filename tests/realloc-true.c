
int main(void)
{
	int *mem = malloc(12);
	*(mem + 1) = 13;
	int *mem2 = realloc(mem, 24);
	__VERIFIER_assert(*(mem2 + 1) == 13);
	free(mem2);
}
