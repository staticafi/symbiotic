if (NOT ${LLVM_PACKAGE_VERSION} VERSION_GREATER "3.4")
  set(LLVM_LINK_COMPONENTS core engine)
endif()

add_llvm_loadable_module(LLVMsvc15
				Prepare.cpp
				InitializeUninitialized.cpp
				RemoveInfiniteLoops.cpp
				DeleteUndefined.cpp
				ReplaceUBSan.cpp
				CheckUnsupported.cpp)
