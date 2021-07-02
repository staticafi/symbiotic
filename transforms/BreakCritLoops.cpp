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

#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"

using namespace llvm;

class BreakCritLoops : public FunctionPass {
  public:
    static char ID;

    BreakCritLoops() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);


bool BreakCritLoops::runOnFunction(Function &F) {
  std::vector<BasicBlock *> to_process;
  for (BasicBlock& block : F) {
    // if this is a block that jumps on itself via a crit edge
    // (from simplifycfg pass), split off the branching condition.
    // It will make the control dependence algorithm work well.
    if (block.size() <= 1)
        continue;

    auto term = block.getTerminator();
    if (BranchInst *BI = dyn_cast<BranchInst>(term)) {
        if (BI->isUnconditional())
            continue;

        for (auto succBB : BI->successors()) {
            auto succssSuccessor = succBB->getUniqueSuccessor();
            if (succssSuccessor && succssSuccessor == &block)
                to_process.push_back(&block);
        }
    }

  }

  for (auto block : to_process) {
    block->splitBasicBlock(--block->end(), "crit.blk.split");
    if (!CloneMetadata(block->getTerminator(), block->getTerminator())) {
        llvm::errs() << "[BreakCritLoops] Failed assigning metadata to: "
                     << *block->getTerminator() << "\n";
    }
  }

  if (to_process.empty())
      return false;

  llvm::errs() << "Split a basic block in " << F.getName() << "\n";
  return true;
}

static RegisterPass<BreakCritLoops> BCL("break-crit-loops",
                                        "transform loops that are in for ugly for "
                                        "the slicer to a better form for the slicer");
char BreakCritLoops::ID;

