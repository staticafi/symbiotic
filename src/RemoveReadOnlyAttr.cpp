//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_os_ostream.h"

using namespace llvm;

// When checking for memory safety, it may happen
// that a bug is in a function that have no side effects
// and the return value is unused (e.g. because slicer
// removed it). LLVM drops calls to such functions
// (instrcombine optimization in particular), but we do
// not want to, because they contain the bug
// (LLVM does not care that the function may not return
// because of an assertion).
// This pass removes readonly attribute from functions
// that we instrumented, so that LLVM may not
// consider them as side-effect free.
namespace {
  class RemoveROAttrs : public ModulePass {
public:
  static char ID;

  RemoveROAttrs() : ModulePass(ID) {}
  virtual bool runOnModule(Module &M);

private:
  bool shouldRemoveROAttr(const Function& F) const {
    // check whether this function is instrumented
    // or whether it contains some call via function pointer
    // (in which case we do not know anything).
    for (const BasicBlock& BB : F) {
      for (const Instruction& I : BB) {
        if (const CallInst *CI = dyn_cast<CallInst>(&I)) {
          const Function *calledF = CI->getCalledFunction();
          // function pointer
          if (calledF == nullptr)
            return true;

          // this function is instrumented
          if (calledF->getName().startswith("__INSTR"))
            return true;
        }
      }
    }
  }

  // remove the readonly attribute from F
  // and also from all functions that call F
  void removeROAttr(Function& F) {
    F.removeFnAttr(Attribute::ReadOnly);

    for (auto use_it = F.use_begin(), use_end = F.use_end();
         use_it != use_end; ++use_it) {
#if ((LLVM_VERSION_MAJOR == 3) && (LLVM_VERSION_MINOR < 5))
      CallInst *CI = dyn_cast<CallInst>(*use_it);
#else
      CallInst *CI = dyn_cast<CallInst>(use_it->getUser());
#endif
      if (CI) {
        Function *parent = CI->getParent()->getParent();
        if (parent)
          removeROAttr(*parent);
      }
    }
  }
};

static RegisterPass<RemoveROAttrs> RROATTRS("remove-readonly-attr",
                                            "Remove read-only attribute from selected funs");
char RemoveROAttrs::ID;

bool RemoveROAttrs::runOnModule(Module &M) {
  bool changed = false;
  for (Function& F : M) {
    if (F.hasFnAttribute(Attribute::ReadOnly) && shouldRemoveROAttr(F)) {
      removeROAttr(F);
      changed = true;
    }
  }

  return changed;
}

}

