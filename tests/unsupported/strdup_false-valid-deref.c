// reach and also memsafety

int main(void) {
	char *x = malloc(21);
	if (!x)
		return 0;
	x[20] = 0;
	char *p = strdup(x);
	// p may be NULL, here can be an invalid dereference
	__VERIFIER_assert(strcmp(x, p) == 0);
	free(x);
	free(p);
	return 0;
}
