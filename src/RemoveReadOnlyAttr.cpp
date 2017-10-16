//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <set>

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
  std::set<Function *> visitedFuns;

  // remove the readonly attribute from F
  // and also from all functions that call F
  bool removeROAttrFromCallers(Function& F) {
    bool changed = false;
    for (auto use_it = F.use_begin(), use_end = F.use_end();
         use_it != use_end; ++use_it) {
#if ((LLVM_VERSION_MAJOR == 3) && (LLVM_VERSION_MINOR < 5))
      CallInst *CI = dyn_cast<CallInst>(*use_it);
#else
      CallInst *CI = dyn_cast<CallInst>(use_it->getUser());
#endif
      if (CI) {
        Function *parent = CI->getParent()->getParent();
        if (parent) {
            // do not visit a function multiple times
            // and leave out functions from instrumentation
            if (parent->getName().startswith("__INSTR"))
              continue;

            if (!visitedFuns.insert(parent).second)
              continue;

            // continue recursively
            changed |= parent->hasFnAttribute(Attribute::ReadOnly);
            parent->removeFnAttr(Attribute::ReadOnly);
            //llvm::errs() << "Removed 'readonly' attr from "
            //             << parent->getName() << "\n";

            changed |= removeROAttrFromCallers(*parent);
        }
      }
    }

    return changed;
  }
};

static RegisterPass<RemoveROAttrs> RROATTRS("remove-readonly-attr",
                                            "Remove read-only attribute from selected funs");
char RemoveROAttrs::ID;

bool RemoveROAttrs::runOnModule(Module &M) {
  bool changed = false;
  for (Function& F : M) {
    if (F.getName().startswith("__INSTR")) {
      changed |= removeROAttrFromCallers(F);
    }
  }

  return changed;
}

}

