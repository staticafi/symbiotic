cmake_minimum_required(VERSION 3.3)
project(sbt-transforms CXX)

# --------------------------------------------------
# Build type
# --------------------------------------------------
if(NOT CMAKE_BUILD_TYPE)
  message(STATUS "Build type not set. Setting default.")
  set(CMAKE_BUILD_TYPE "RelWithDebInfo" CACHE STRING "" FORCE)
endif()
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "RelWithDebInfo"
                                                     "MinSizeRel" "Release")

# --------------------------------------------------
# Compiler flags
# --------------------------------------------------
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fno-rtti -Wall -Wextra -pedantic")

# --------------------------------------------------
# LLVM
# --------------------------------------------------
find_package(LLVM REQUIRED CONFIG)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")
message(STATUS "LLVM definitions: ${LLVM_DEFINITIONS}")
message(STATUS "LLVM include dir: ${LLVM_INCLUDE_DIRS}")
message(STATUS "LLVM libraries dir: ${LLVM_LIBRARY_DIRS}")

list(APPEND CMAKE_MODULE_PATH "${LLVM_DIR}")
include(AddLLVM)

# TODO: move this to the section above when we switch to C++14
# LLVM 10 and newer require at least C++14 standard
if (${LLVM_PACKAGE_VERSION} VERSION_GREATER "9.0")
  set(CMAKE_CXX_STANDARD 14)
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14")
else()
  # otherwise we need C++11 standard
  set(CMAKE_CXX_STANDARD 11)
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
endif()

add_definitions(${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})
link_directories(${LLVM_LIBRARY_DIRS})

# --------------------------------------------------
# Set correct install directories
# --------------------------------------------------
include(GNUInstallDirs)
message(STATUS "CMAKE_INSTALL_LIBDIR: \"${CMAKE_INSTALL_LIBDIR}\"")

# --------------------------------------------------
# LLVMsbt
# --------------------------------------------------
add_library(LLVMsbt MODULE "AInliner.cpp"
                           "BreakCritLoops.cpp"
                           "BreakInfiniteLoops.cpp"
                           "CheckModule.cpp"
                           "ClassifyInstructions.cpp"
                           "ClassifyLoops.cpp"
                           "CloneMetadata.cpp"
                           "CountInstr.cpp"
                           "DeleteUndefined.cpp"
                           "DummyMarker.cpp"
                           "ExplicitConsdes.cpp"
                           "FindExits.cpp"
                           "FlattenLoops.cpp"
                           "InitializeUninitialized.cpp"
                           "InstrumentAlloc.cpp"
                           "InstrumentNontermination.cpp"
                           "InternalizeGlobals.cpp"
                           "MakeNondet.cpp"
                           "MarkVolatile.cpp"
                           "DeleteCalls.cpp"
                           "GetTestTargets.cpp"
                           "PrepareOverflows.cpp"
                           "RemoveErrorCalls.cpp"
                           "RemoveConstantExprs.cpp"
                           "RemoveInfiniteLoops.cpp"
                           "RemoveReadOnlyAttr.cpp"
                           "RenameVerifierFuns.cpp"
                           "ReplaceAsserts.cpp"
                           "ReplaceLifetimeMarkers.cpp"
                           "ReplaceUBSan.cpp"
                           "ReplaceVerifierAtomic.cpp"
                           "Unrolling.cpp"
)

# remove lib prefix for compatibility with older releases
set_target_properties(LLVMsbt PROPERTIES PREFIX "")

install(TARGETS LLVMsbt
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
