typedef signed long int time_t;

time_t time(time_t *tloc) {
	time_t ret;
	klee_make_symbolic(&ret, sizeof(ret), "nondet_time");
	klee_assume(ret >= -1);
	if (tloc)
		*tloc = ret;

	return ret;
}
