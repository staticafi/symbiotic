cmake_minimum_required(VERSION 3.3)
project(sbt-transforms)

find_package(LLVM REQUIRED CONFIG)

list(APPEND CMAKE_MODULE_PATH "${LLVM_DIR}")
list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")

if (${LLVM_PACKAGE_VERSION} VERSION_LESS_EQUAL "3.7")
  # needed for LLVM 3.7
  set(LLVM_RUNTIME_OUTPUT_INTDIR ${CMAKE_BINARY_DIR}/${CMAKE_CFG_INTDIR})
  set(LLVM_LIBRARY_OUTPUT_INTDIR ${CMAKE_BINARY_DIR}/${CMAKE_CFG_INTDIR})
  include(HandleLLVMOptions)
endif()

include(LLVMConfig)
include(AddLLVM)

# explicitly add -std=c++11 (c++14), some cmake versions
# fail adding it even with CMAKE_CXX_STANDARD,
# LLVM 10 and newer require at least C++14 standard
if (${LLVM_PACKAGE_VERSION} VERSION_GREATER_EQUAL "10.0")
  set(CMAKE_CXX_STANDARD 14)
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14")
else()
  # otherwise we need C++11 standard
  set(CMAKE_CXX_STANDARD 11)
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
endif()

set(CMAKE_CXX_STANDARD_REQUIRED on)
set(CMAKE_CXX_EXTENSIONS off)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -pedantic -Wno-unused-parameter -Wno-unused-variable -fno-rtti")

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

set(CPPFILES "CloneMetadata.cpp"
	     "CheckModule.cpp"
	     "RemoveReadOnlyAttr.cpp"
	     "RemoveErrorCalls.cpp"
	     "FindExits.cpp"
	     "RenameVerifierFuns.cpp"
	     "MakeNondet.cpp"
	     "InitializeUninitialized.cpp"
	     "InternalizeGlobals.cpp"
	     "RemoveInfiniteLoops.cpp"
	     "BreakInfiniteLoops.cpp"
	     "BreakCritLoops.cpp"
	     "DeleteUndefined.cpp"
	     "ReplaceUBSan.cpp"
	     "ReplaceAsserts.cpp"
	     "InstrumentAlloc.cpp"
	     "CountInstr.cpp"
	     "MarkVolatile.cpp"
	     "DummyMarker.cpp"
	     "ReplaceLifetimeMarkers.cpp"
	     "ReplaceVerifierAtomic.cpp"
	     "Unrolling.cpp"
	     "InstrumentNontermination.cpp"
	     "ClassifyLoops.cpp"
	     "ClassifyInstructions.cpp"
	     "Prepare.cpp"
	     "PrepareOverflows.cpp")

if (${LLVM_PACKAGE_VERSION} VERSION_LESS "8")
	add_llvm_loadable_module(LLVMsbt ${CPPFILES})
else()
	add_llvm_library(LLVMsbt MODULE ${CPPFILES})
endif()

install(TARGETS LLVMsbt
	LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
