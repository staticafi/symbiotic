add_subdirectory(lib)
add_subdirectory(include)

install(PROGRAMS scripts/symbiotic
	DESTINATION bin)
