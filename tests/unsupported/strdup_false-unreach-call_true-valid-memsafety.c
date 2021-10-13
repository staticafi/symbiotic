// reach and also memsafety

int main(void) {
	char *x = malloc(21);
	if (!x)
		return 0;
	x[20] = 0;
	char *p = strdup(x);
	if (!p) {
		free(x);
		return 0;
	}
	__VERIFIER_assert(strcmp(x, p) != 0);
	free(x);
	free(p);
	return 0;
}
