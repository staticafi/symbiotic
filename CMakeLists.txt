cmake_minimum_required(VERSION 2.8)
project(symbiotic)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED on)
# explicitly add -std=c++11, some cmake versions
# fail adding it even with CMAKE_CXX_STANDARD
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

find_package(LLVM REQUIRED CONFIG)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${LLVM_DIR}")

include(LLVMConfig)
include(AddLLVM)

if (NOT ${LLVM_PACKAGE_VERSION} VERSION_GREATER "3.4")
  llvm_replace_compiler_option(CMAKE_CXX_FLAGS "-frtti" "-fno-rtti")
endif()

set(INSTALL_BIN_DIR ${CMAKE_INSTALL_PREFIX} CACHE PATH "Installation directory for executables")
set(INSTALL_INC_DIR include CACHE PATH "Installation directory for headers")
set(INSTALL_DATA_DIR ${CMAKE_INSTALL_PREFIX} CACHE PATH "Installation directory for data files")

add_definitions(${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})
link_directories(${LLVM_LIBRARY_DIRS})

find_path(LLVM_SRC_PATH include/llvm/Module.h)
find_path(LLVM_BUILD_PATH include/llvm/Intrinsics.gen)

if (LLVM_SRC_PATH)
  include_directories(${LLVM_SRC_PATH}/include)
endif(LLVM_SRC_PATH)
if (LLVM_BUILD_PATH)
  include_directories(${LLVM_BUILD_PATH}/include)
  link_directories(${LLVM_BUILD_PATH}/lib)
endif(LLVM_BUILD_PATH)

add_subdirectory(src)
add_subdirectory(lib)
add_subdirectory(include)

install(PROGRAMS scripts/symbiotic
	DESTINATION bin)
