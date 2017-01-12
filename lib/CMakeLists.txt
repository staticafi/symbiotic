# verifer functions
install(FILES
		verifier/__VERIFIER_calloc.c
		verifier/__VERIFIER_calloc0.c
		verifier/__VERIFIER_malloc.c
		verifier/__VERIFIER_malloc0.c
		verifier/__VERIFIER_error.c
		verifier/__VERIFIER_exit.c
		verifier/__VERIFIER_assert.c
		verifier/__VERIFIER_assume.c
		verifier/__VERIFIER_make_symbolic.c
		verifier/__VERIFIER_nondet__Bool.c
		verifier/__VERIFIER_nondet_bool.c
		verifier/__VERIFIER_nondet_char.c
		verifier/__VERIFIER_nondet_double.c
		verifier/__VERIFIER_nondet_float.c
		verifier/__VERIFIER_nondet_int.c
		verifier/__VERIFIER_nondet_long.c
		verifier/__VERIFIER_nondet_pchar.c
		verifier/__VERIFIER_nondet_pointer.c
		verifier/__VERIFIER_nondet_short.c
		verifier/__VERIFIER_nondet_uchar.c
		verifier/__VERIFIER_nondet_uint.c
		verifier/__VERIFIER_nondet_ulong.c
		verifier/__VERIFIER_nondet_unsigned.c
		verifier/__VERIFIER_nondet_ushort.c
		verifier/__VERIFIER_nondet_u16.c
		verifier/__VERIFIER_nondet_u32.c
		verifier/__VERIFIER_nondet_u8.c
		verifier/__VERIFIER_nondet_U16.c
		verifier/__VERIFIER_nondet_U32.c
		verifier/__VERIFIER_nondet_U8.c
		verifier/__VERIFIER_nondet_size_t.c
		verifier/__VERIFIER_nondet_loff_t.c
		verifier/__VERIFIER_nondet_sector_t.c
	DESTINATION ${INSTALL_DATA_DIR}/lib/verifier)

# std functions
install(FILES
		libc/strlen.c
		libc/memcmp.c
		libc/memcpy.c
		libc/memchr.c
		libc/memrchr.c
		libc/memmove.c
		libc/strchr.c
		libc/strrchr.c
		libc/strcmp.c
		libc/strcpy.c
		libc/strncmp.c
		libc/strncpy.c
		libc/strtoul.c
		libc/strtoull.c
		libc/strtod.c
		libc/atoi.c
		libc/strerror.c
		libc/localtime.c
		libc/strspn.c
		libc/strcspn.c
		libc/getenv.c
		libc/__ctype_b_loc.c
		libc/__errno_location.c
	DESTINATION ${INSTALL_DATA_DIR}/lib/libc)

# linux kernel functions
install(FILES
		kernel/kzalloc.c
		kernel/__kfree.c
		kernel/__kmalloc.c
		kernel/kfree.c
		kernel/kmalloc.c
		kernel/__memcpy.c
		kernel/__memset.c
		kernel/_ctype.c
	DESTINATION ${INSTALL_DATA_DIR}/lib/kernel)

