//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <set>

#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_os_ostream.h"
#include "llvm/Transforms/Utils/Cloning.h"
//#include "llvm/Analysis/CallGraph.h"

using namespace llvm;

class AgressiveInliner : public ModulePass {
public:
  static char ID;

  AgressiveInliner() : ModulePass(ID) {}

  bool runOnModule(Module& M) override;
  bool runOnFunction(Function &F);
};

static RegisterPass<AgressiveInliner>
DLTU("ainline", "Agressive inliner - inline as much as you can.");

char AgressiveInliner::ID;

bool AgressiveInliner::runOnModule(Module& M) {
  bool changed = false;
  for (auto& F : M) {
      changed |= runOnFunction(F);
  }
  return changed;
}

bool AgressiveInliner::runOnFunction(Function &F) {
    bool changed = false;
    std::vector<CallInst *> calls;
    for (auto& B : F) {
        for (auto& I : B) {
            if (auto *CI = dyn_cast<CallInst>(&I)) {
                calls.push_back(CI);
            }
        }
    }

    // FIXME: this is really stupid naive way to inline...
    for (auto *CI : calls) {
        //llvm::errs() << "Inlining: " <<*CI << "\n";
        InlineFunctionInfo IFI;
        auto result = InlineFunction(CI, IFI);
        if (!result) {
           //llvm::errs() << "Failed inlining: " << *CI << "\n";
           //llvm::errs() << "  " << static_cast<const char *>(result) << "\n";
        } else {
            changed = true;
        }
    }

    return changed;
}

