/*
 * The position of the least significant set bit (counted from 1), or 0 if
 * no bit is set. Without branches, so that a symbolic argument does not fork
 * the execution into 33 paths.
 */
int ffs(int i)
{
	unsigned x = (unsigned) i & (0u - (unsigned) i); /* the lowest set bit */
	int pos = 1 + 16 * ((x & 0xFFFF0000u) != 0)
	            + 8 * ((x & 0xFF00FF00u) != 0)
	            + 4 * ((x & 0xF0F0F0F0u) != 0)
	            + 2 * ((x & 0xCCCCCCCCu) != 0)
	            + ((x & 0xAAAAAAAAu) != 0);
	return pos * (x != 0);
}
