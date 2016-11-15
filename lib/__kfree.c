extern void free(void *);

void __kfree(void *mem)
{
	(void) free(mem);
}
