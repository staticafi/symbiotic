char *strcpy(char *dest, const char *src)
{
	int i = 0;

	while(src[i] != '\0') {
		dest[i] = src[i];
		++i;
	}

	/* include the terminating 0 */
	dest[i] = '\0';

	return dest;
}

