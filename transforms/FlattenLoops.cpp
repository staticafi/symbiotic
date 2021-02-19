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

bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);

class FlattenLoops : public LoopPass {
  public:
    static char ID;

    FlattenLoops() : LoopPass(ID) {}

    // FIXME: properly change the structure of LoopInfo
    bool runOnLoop(Loop *L, LPPassManager &LPM) override {
        auto *PL = L->getParentLoop();
        if (!PL)
            return false;

        auto *parentheader = PL->getHeader();
        auto *innerheader = L->getHeader();
        auto *fun = parentheader->getParent();
        auto& Ctx = fun->getParent()->getContext();
        
        BasicBlock *flaginit = BasicBlock::Create(Ctx, "flatten.init",
                                                  fun, parentheader);
        BasicBlock *newheaderbb = BasicBlock::Create(Ctx, "flatten.loop.header",
                                                     fun, parentheader);

        // flag whether we are in the inner or outer loop
        // initialize "inner" to 0
        auto& entrybb = fun->getEntryBlock();
        AllocaInst *flag = new AllocaInst(Type::getInt8Ty(Ctx), 0,
                                          "inner");
        flag->insertBefore(&*entrybb.getFirstInsertionPt());
        auto *SI = new StoreInst(ConstantInt::get(Type::getInt8Ty(Ctx), 0), flag);
        SI->insertAfter(flag);
        BranchInst::Create(newheaderbb, flaginit);

        SmallVector<llvm::BasicBlock *, 2> exits;
        L->getExitBlocks(exits);
        for (auto *outbb : exits) {
            // set inner to 0
            new StoreInst(ConstantInt::get(Type::getInt8Ty(Ctx), 0), flag,
                          &*outbb->getFirstInsertionPt());
        }

        // redirect edges that jump to the inner header
        std::set<BranchInst *> jumpsToHeader;
        for (auto *pred : predecessors(innerheader)) {
            jumpsToHeader.insert(cast<BranchInst>(pred->getTerminator()));
        }

        for (auto *pBI : jumpsToHeader) {
            unsigned idx = 0;
            for (auto* succ : pBI->successors()) {
                if (succ == innerheader) {
                    pBI->setSuccessor(idx, newheaderbb);
                    // set inner flag to true
                    if (!L->contains(pBI->getParent())) {
                        new StoreInst(ConstantInt::get(Type::getInt8Ty(Ctx), 1),
                                      flag, pBI);
                    }
                }
                ++idx;
            }
        }

        // redirect edges that go to parent header to the new header
        std::set<BranchInst *> jumpsToParentHeader;
        std::set<BranchInst *> backedgesToParentHeader;
        for (auto *pred : predecessors(parentheader)) {
            if (PL->contains(pred))
                backedgesToParentHeader.insert(cast<BranchInst>(pred->getTerminator()));
            else
                jumpsToParentHeader.insert(cast<BranchInst>(pred->getTerminator()));
        }

        for (auto *pBI : jumpsToParentHeader) {
            unsigned idx = 0;
            for (auto* succ : pBI->successors()) {
                if (succ == parentheader) {
                    pBI->setSuccessor(idx, flaginit);
                }
                ++idx;
            }
        }

        for (auto *pBI : backedgesToParentHeader) {
            unsigned idx = 0;
            for (auto* succ : pBI->successors()) {
                if (succ == parentheader) {
                    pBI->setSuccessor(idx, newheaderbb);
                }
                ++idx;
            }
        }

        // NOTE: we must create the branch inst only now
        // so that we do not change its successors
        auto *LI = new LoadInst(Type::getInt8Ty(Ctx), flag,
                                "innerval", newheaderbb);
        auto *Cmp = new ICmpInst(ICmpInst::ICMP_EQ,
                            ConstantInt::get(Type::getInt8Ty(Ctx), 1),
                            LI);
        Cmp->insertAfter(LI);
        auto *Br = BranchInst::Create(innerheader, parentheader, Cmp, newheaderbb);

        // This is an ugly hack -- we use this message to find out
        // that we transformed the code. FIXME: invalidate the analysis
        // and properly adjust LoopInfo to flatten all loops at once.
        llvm::errs() << "Flattened a loop\n";

        // update the LoopPass - add the new block and make it a header
        PL->addBlockEntry(newheaderbb);
        PL->moveToHeader(newheaderbb);
        PL->removeChildLoop(L);
        return true;
    }

    // XXX: we should set preserved analyses
};

static RegisterPass<FlattenLoops> RIL("flatten-loops",
                                       "Flatten nested loops into non-nested loops");
char FlattenLoops::ID;

