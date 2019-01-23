#include <assert.h>
#include <ctype.h>

int main(void)
{
	__VERIFIER_assert(isspace(' '));
	__VERIFIER_assert(isdigit('8'));
	__VERIFIER_assert(!isdigit(' '));
	__VERIFIER_assert(!isspace('8'));
	__VERIFIER_assert(!isblank('1'));

	return 0;
}
