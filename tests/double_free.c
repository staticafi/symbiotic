int main(void)
{
	int *p = malloc(sizeof *p);
	free(p);
	free(p);

	return 0;
}
