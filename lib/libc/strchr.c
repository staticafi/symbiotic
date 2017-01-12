char *strchr(const char *str, int c)
{
	while (*str != '\0') {
		if (*str == c)
			return (char *) str;
		else
			++str;
	}

	return ((char *) 0);
}
