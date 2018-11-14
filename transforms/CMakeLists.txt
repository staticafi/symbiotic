cmake_minimum_required(VERSION 3.3)
project(sbt-transforms)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED on)
# explicitly add -std=c++11, some cmake versions
# fail adding it even with CMAKE_CXX_STANDARD
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

find_package(LLVM REQUIRED CONFIG)

list(APPEND CMAKE_MODULE_PATH "${LLVM_DIR}")
list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")

# needed for LLVM 3.7
set(LLVM_RUNTIME_OUTPUT_INTDIR ${CMAKE_BINARY_DIR}/${CMAKE_CFG_INTDIR})
set(LLVM_LIBRARY_OUTPUT_INTDIR ${CMAKE_BINARY_DIR}/${CMAKE_CFG_INTDIR})
include(HandleLLVMOptions)

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

include(GNUInstallDirs)
message(STATUS "CMAKE_INSTALL_LIBDIR: \"${CMAKE_INSTALL_LIBDIR}\"")
message(STATUS "CMAKE_INSTALL_INCLUDEDIR: \"${CMAKE_INSTALL_INCLUDEDIR}\"")



# We need all the symbols with dynamic libs. With static libs, we get errors.
if (BUILD_SHARED_LIBS)
	set(LLVM_LINK_COMPONENTS analysis core support)
endif()

add_llvm_loadable_module(LLVMsbt
				CloneMetadata.cpp
				Prepare.cpp
				RemoveReadOnlyAttr.cpp
				RemoveErrorCalls.cpp
				RenameVerifierFuns.cpp
				InitializeUninitialized.cpp
				RemoveInfiniteLoops.cpp
				BreakInfiniteLoops.cpp
				BreakCritLoops.cpp
				DeleteUndefined.cpp
				ReplaceUBSan.cpp
				InstrumentAlloc.cpp
				CountInstr.cpp
				MarkVolatile.cpp
				CheckUnsupported.cpp
				PrepareOverflows.cpp)

install(TARGETS LLVMsbt
	LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
