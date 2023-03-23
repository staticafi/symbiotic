static int __symbiotic_errno = 0;
int *__errno_location(void)
{
	/* we don't support multi-threaded programs,
	 * so we can have just this one errno */
	return &__symbiotic_errno;
}
