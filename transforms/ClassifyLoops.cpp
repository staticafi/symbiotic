//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <vector>

#include "llvm/IR/DataLayout.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/IR/Type.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

// for checking irreducibility
#include "llvm/Analysis/LoopIterator.h"
#include "llvm/Analysis/CFG.h"

#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"

using namespace llvm;

class ClassifyLoops : public LoopPass {
   bool any{false};
   bool nested{false};
   bool nonterm{false};
   bool irreducible{false};

   public:
    static char ID;

    ClassifyLoops() : LoopPass(ID) {}

    void getAnalysisUsage(AnalysisUsage &AU) const override {
      AU.setPreservesCFG();
      AU.addRequired<LoopInfoWrapperPass>();
    }

    bool runOnLoop(Loop *L, LPPassManager & /*LPM*/) override {
      any = true;

      // for now, we detect only nested loops
      if (L->getParentLoop()) {
          nested = true;
      }

      if (!nonterm) {
        SmallVector<llvm::BasicBlock *, 8> ExitBlocks;
        L->getExitBlocks(ExitBlocks);
        if (ExitBlocks.size() == 0) {
          nonterm = true;
        }
      }

      if (!irreducible) {
#if LLVM_VERSION_MAJOR > 6
        // XXX: hmm, not sure this is working...
        LoopInfo &LI = getAnalysis<LoopInfoWrapperPass>().getLoopInfo();
        LoopBlocksRPO RPOT(L);
        RPOT.perform(&LI);
        irreducible = containsIrreducibleCFG<const BasicBlock *>(RPOT, LI);
#endif
      }

      return false;
    }

    bool doFinalization() override {
      if (any) {
          llvm::errs() << "contains loops\n";
          if (nested)
              llvm::errs() << "  nested loops\n";
          if (nonterm)
              llvm::errs() << "  nonterm loops\n";
          if (irreducible)
              llvm::errs() << "  irreducible loops\n";
      }
      return false;
    }
};

static RegisterPass<ClassifyLoops> CL("classify-loops",
                                      "detect what loops are in the program");
char ClassifyLoops::ID;

