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
    UnreachableInst *UI = new UnreachableInst(Ctx, exitBB);

    _exitBBs.emplace(F, exitBB);
    return exitBB;
  }

  public:
    static char ID;

    BreakInfiniteLoops() : LoopPass(ID) {}

    virtual bool runOnLoop(Loop *L, LPPassManager &LPM) override {
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

        TerminatorInst *headerTI = header->getTerminator();

        // add a new block to which we jump from the header and in
        // this new block we always jump to the original successor,
        // but we also jump outside of the loop (which will never
        // occur during runtime)
        BasicBlock *exitBB = getExitBB(header->getParent());
        BasicBlock *nb = BasicBlock::Create(Ctx, "break.inf.loop");
        LoadInst *LI = new LoadInst(getConstantTrueGV(*M), "always_true", nb);
        BranchInst *BI = BranchInst::Create(headerTI->getSuccessor(0), exitBB, LI, nb);
        nb->insertInto(header->getParent(), headerTI->getSuccessor(0));
        headerTI->setSuccessor(0, nb);

        // update the LoopPass
        L->addBlockEntry(nb);
        return true;
    }

    // XXX: we should set preserved analyses
};

static RegisterPass<BreakInfiniteLoops> RIL("break-infinite-loops",
                                             "transform loops that has no exit to loops "
                                             "that has an exit");
char BreakInfiniteLoops::ID;

