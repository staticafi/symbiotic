int main(void) {
	int *p = malloc(10);
	free(++p);
	return 0;
}
