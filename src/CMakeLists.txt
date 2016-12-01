# We need all the symbols with dynamic libs. With static libs, we get errors.
if (BUILD_SHARED_LIBS)
	set(LLVM_LINK_COMPONENTS analysis core support)
endif()

add_llvm_loadable_module(LLVMsvc15
				Prepare.cpp
				InitializeUninitialized.cpp
				RemoveInfiniteLoops.cpp
				BreakInfiniteLoops.cpp
				DeleteUndefined.cpp
				ReplaceUBSan.cpp
				InstrumentAlloc.cpp
				FindInit.cpp
				CheckUnsupported.cpp)

install(TARGETS LLVMsvc15
	LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
