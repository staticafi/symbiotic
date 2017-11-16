struct test_statics
{
  signed int ngroups;
};

extern struct test_statics * const test_ptr_to_statics;

int main()
{
  void *mem =malloc(sizeof(struct test_statics) );
  *((struct test_statics **)&test_ptr_to_statics) = (struct test_statics *)mem;
  free((void *)test_ptr_to_statics);
  return 0;
}
