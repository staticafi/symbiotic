extern void free(void *);

void kfree(void *mem)
{
	(void) free(mem);
}
