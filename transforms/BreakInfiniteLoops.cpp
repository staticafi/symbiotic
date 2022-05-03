//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <map>
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

bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);

class BreakInfiniteLoops : public LoopPass {
  std::map<Function *, BasicBlock *> _exitBBs;
  GlobalVariable *_trueGV = nullptr;

  GlobalVariable *getConstantTrueGV(Module& M) {
    if (_trueGV)
      return _trueGV;

    LLVMContext& Ctx = M.getContext();
    _trueGV = new GlobalVariable(M, Type::getInt1Ty(Ctx), true /*constant */,
                                 GlobalVariable::PrivateLinkage,
                                 ConstantInt::getTrue(Ctx),
                                 "always_true");

    return _trueGV;
  }

  BasicBlock *getExitBB(Function *F) {
    auto it = _exitBBs.find(F);
    if (it != _exitBBs.end())
      return it->second;

    LLVMContext& Ctx = F->getParent()->getContext();
    BasicBlock *exitBB = BasicBlock::Create(Ctx, "inf.loop.exit", F);
    new UnreachableInst(Ctx, exitBB);

    _exitBBs.emplace(F, exitBB);
    return exitBB;
  }

  public:
    static char ID;

    BreakInfiniteLoops() : LoopPass(ID) {}

    virtual bool runOnLoop(Loop *L, LPPassManager & /*LPM*/) override {
        SmallVector<llvm::BasicBlock *, 2> exits;
        L->getExitingBlocks(exits);
        if (!exits.empty())
          return false;

        // we found an (syntatically) infinite loop, like while(1){},
        // let's break it by something like int a = 1; while(a) {}.
        // The loop will remain infinite semantically, but it will
        // have an exit edge that it never executes
        BasicBlock *header = L->getHeader();
        Module *M = header->getParent()->getParent();
        LLVMContext& Ctx = M->getContext();

        // we will change predecessors of the header - instead of making them jump
        // on the header, make them jump on the new block.
        // First gather the jumps to the header block (to a new container,
        // so that we do not corrupt the iterator). We must do it here,
        // before we make the new block jumping to the header
        std::vector<std::pair<BasicBlock *, unsigned>> to_change;
        for (auto I = pred_begin(header), E = pred_end(header); I != E; ++I) {
          auto TI = (*I)->getTerminator();
          for (int i = 0, e = TI->getNumSuccessors(); i < e; ++i) {
            if (TI->getSuccessor(i) == header)
              to_change.emplace_back(*I, i);
          }
        }

        // add a new block from which we conditionally jump to the header.
        // The condition will be always true, so the program won't change,
        // except there will be an edge exiting the loop, which is what
        // we need.
        BasicBlock *exitBB = getExitBB(header->getParent());
        BasicBlock *nb = BasicBlock::Create(Ctx, "break.inf.loop");

        GlobalVariable * gv = getConstantTrueGV(*M);
        LoadInst *LI = new LoadInst(
            gv->getType()->getPointerElementType(),
            gv,
            "always_true",
            nb);

        if (!CloneMetadata(header->getTerminator(), LI)) {
            llvm::errs() << "[BreakInfiniteLoops] Failed assigning metadata to: "
                         << *LI << "\n";
        }

        auto Br = BranchInst::Create(header, exitBB, LI, nb);
        if (!CloneMetadata(header->getTerminator(), Br)) {
            llvm::errs() << "[BreakInfiniteLoops] Failed assigning metadata to: "
                         << *Br << "\n";
        }

        // insert the new block before header
        nb->insertInto(header->getParent(), header);

        // now change the jump instructions
        for (auto& pr : to_change) {
          auto TI = pr.first->getTerminator();
          TI->setSuccessor(pr.second, nb);
        }

        // update the LoopPass - add the new block and make it a header
        L->addBlockEntry(nb);
        L->moveToHeader(nb);
        return true;
    }

    // XXX: we should set preserved analyses
};

static RegisterPass<BreakInfiniteLoops> RIL("break-infinite-loops",
                                             "transform loops that has no exit to loops "
                                             "that has an exit");
char BreakInfiniteLoops::ID;

