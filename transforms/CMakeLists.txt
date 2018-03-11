# We need all the symbols with dynamic libs. With static libs, we get errors.
if (BUILD_SHARED_LIBS)
	set(LLVM_LINK_COMPONENTS analysis core support)
endif()

add_llvm_loadable_module(LLVMsbt
				CloneMetadata.cpp
				Prepare.cpp
				RemoveReadOnlyAttr.cpp
				RenameVerifierFuns.cpp
				InitializeUninitialized.cpp
				RemoveInfiniteLoops.cpp
				BreakInfiniteLoops.cpp
				DeleteUndefined.cpp
				ReplaceUBSan.cpp
				InstrumentAlloc.cpp
				CountInstr.cpp
				CheckUnsupported.cpp)

install(TARGETS LLVMsbt
	LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
