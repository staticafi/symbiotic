# verifer functions
install(DIRECTORY verifier
	DESTINATION ${INSTALL_DATA_DIR}/lib)

# std functions
install(DIRECTORY libc
	DESTINATION ${INSTALL_DATA_DIR}/lib)

install(DIRECTORY posix
	DESTINATION ${INSTALL_DATA_DIR}/lib)

# linux kernel functions
install(DIRECTORY kernel
	DESTINATION ${INSTALL_DATA_DIR}/lib)

