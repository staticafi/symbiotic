#include <time.h>

extern int __VERIFIER_nondet_int(void);

static struct tm __localtime;
/* ignores timers, so repeated call to localtime(timer)
 * will yield different results, which is not nice and correct */
struct tm *localtime (const time_t *timer)
{
   __localtime.tm_sec   = __VERIFIER_nondet_int();
   __localtime.tm_min   = __VERIFIER_nondet_int();
   __localtime.tm_hour  = __VERIFIER_nondet_int();
   __localtime.tm_mday  = __VERIFIER_nondet_int();
   __localtime.tm_mon   = __VERIFIER_nondet_int();
   __localtime.tm_year  = __VERIFIER_nondet_int();
   __localtime.tm_wday  = __VERIFIER_nondet_int();
   __localtime.tm_yday  = __VERIFIER_nondet_int();
   /* Daylight saving time */
   __localtime.tm_isdst = __VERIFIER_nondet_int();

   /* Seconds (0-60) */
   __VERIFIER_assume(__localtime.tm_sec >= 0 && __localtime.tm_sec <= 60);
   /* Minutes (0-59) */
   __VERIFIER_assume(__localtime.tm_min >= 0 && __localtime.tm_min < 60);
   /* Hours (0-23) */
   __VERIFIER_assume(__localtime.tm_hour >= 0 && __localtime.tm_hour < 24);
   /* Day of the month (1-31) */
   __VERIFIER_assume(__localtime.tm_mday > 0 && __localtime.tm_mday < 32);
   /* Month (0-11) */
   __VERIFIER_assume(__localtime.tm_mon >= 0 && __localtime.tm_mon < 12);
   /* Year - 1900 */
   /* This is just an approximation */
   __VERIFIER_assume(__localtime.tm_year >= 0 && __localtime.tm_year < 1000);
   /* Day of the week (0-6, Sunday = 0) */
   __VERIFIER_assume(__localtime.tm_wday >= 0 && __localtime.tm_wday < 7);
   /* Day in the year (0-365, 1 Jan = 0) */
   __VERIFIER_assume(__localtime.tm_yday >= 0 && __localtime.tm_yday <= 365);

   return &__localtime;
}

