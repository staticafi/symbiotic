char *strrchr(const char *str, int c)
{
	char *last = ((char *) 0);
	while (*str != '\0') {
		if (*str == c)
			last = (char *) str;
		++str;
	}

	return last;
}
