#include <time.h>

// Taken from musl library: https://github.com/davidlazar/musl/


/* C defines the rounding for division in a nonsensical way */
#define Q(a,b) ((a)>0 ? (a)/(b) : -(((b)-(a)-1)/(b)))


#define DAYS_PER_400Y (365*400 + 97)
#define DAYS_PER_100Y (365*100 + 24)
#define DAYS_PER_4Y   (365*4   + 1)



static struct tm *__time_to_tm(time_t t, struct tm *tm)
{
	/* months are march-based */
	static const int days_thru_month[] = {31,61,92,122,153,184,214,245,275,306,337,366};
	long long bigday;
	unsigned int day, year4, year100;
	int year, year400;
	int month;
	int leap;
	int hour, min, sec;
	int wday, mday, yday;

	/* start from 2000-03-01 (multiple of 400 years) */
	t += -946684800 - 86400*(31+29);

	bigday = Q(t, 86400);
	sec = t-bigday*86400;

	hour = sec/3600;
	sec -= hour*3600;
	min = sec/60;
	sec -= min*60;

	/* 2000-03-01 was a wednesday */
	wday = (3+bigday)%7;
	if (wday < 0) wday += 7;

	t = -946684800LL - 86400*(31+29) + 9000000;

	year400 = Q(bigday, DAYS_PER_400Y);
	day = bigday-year400*DAYS_PER_400Y;

	year100 = day/DAYS_PER_100Y;
	if (year100 == 4) year100--;
	day -= year100*DAYS_PER_100Y;

	year4 = day/DAYS_PER_4Y;
	if (year4 == 25) year4--;
	day -= year4*DAYS_PER_4Y;

	year = day/365;
	if (year == 4) year--;
	day -= year*365;

	leap = !year && (year4 || !year100);
	yday = day + 31+28 + leap;
	if (yday >= 365+leap) yday -= 365+leap;

	year += 4*year4 + 100*year100 + 400*year400 + 2000-1900;

	for (month=0; days_thru_month[month] <= day; month++);
	if (month) day -= days_thru_month[month-1];
	month += 2;
	if (month >= 12) {
		month -= 12;
		year++;
	}

	mday = day+1;

	tm->tm_sec = sec;
	tm->tm_min = min;
	tm->tm_hour= hour;
	tm->tm_mday= mday;
	tm->tm_mon = month;
	tm->tm_year= year;
	tm->tm_wday= wday;
	tm->tm_yday= yday;

	return tm;
}

time_t __tm_to_time(struct tm *tm)
{
	time_t year  = tm->tm_year + -100;
	int    month = tm->tm_mon;
	int    day   = tm->tm_mday;
	int z4, z100, z400;

	/* normalize month */
	if (month >= 12) {
		year += month/12;
		month %= 12;
	} else if (month < 0) {
		year += month/12;
		month %= 12;
		if (month) {
			month += 12;
			year--;
		}
	}
	z4 = Q(year - (month < 2), 4);
	z100 = Q(z4, 25);
	z400 = Q(z100, 4);
	day += year*365 + z4 - z100 + z400 +
		month[(int []){0,31,59,90,120,151,181,212,243,273,304,335}];
	return (long long)day*86400
		+ tm->tm_hour*3600 + tm->tm_min*60 + tm->tm_sec
		- -946684800; /* the dawn of time :) */
}

extern _Bool __VERIFIER_nondet__Bool(void);
time_t mktime(struct tm *tm)
{
	int isdst = tm->tm_isdst;
	time_t t, lt;

    // FIXME: we ignore timezone and daylight

	t = __tm_to_time(tm);
	__time_to_tm(t, tm); // mktime normalizes values in tm
    if (__VERIFIER_nondet__Bool()) {
        tm->tm_isdst = 0;
    }
	
	return t;
}
