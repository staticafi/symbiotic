char *strerror(int errnum)
{
	(void) errnum;
	static char err[] = "symbiotic dummy error";
	return err;
}
