set(INSTALL_BIN_DIR ${CMAKE_INSTALL_PREFIX} CACHE PATH "Installation directory for executables")
set(INSTALL_INC_DIR include CACHE PATH "Installation directory for headers")
set(INSTALL_DATA_DIR ${CMAKE_INSTALL_PREFIX} CACHE PATH "Installation directory for data files")

add_subdirectory(lib)
add_subdirectory(include)

install(PROGRAMS scripts/symbiotic scripts/gen-c scripts/kleetester.py
	DESTINATION bin)

install(DIRECTORY properties
	DESTINATION ${INSTALL_DATA_DIR}/)

