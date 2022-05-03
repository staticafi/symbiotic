#include "llvm/IR/DataLayout.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Type.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

#include "llvm/Pass.h"
#include "llvm/Analysis/LoopPass.h"
#include "llvm/Transforms/Utils/Cloning.h"

#include "llvm/Support/CommandLine.h"

#include <map>

using namespace llvm;

static cl::opt<unsigned> UnrollCount("sbt-loop-unroll-count",
                                   cl::desc("The number of loop unrollings"),
                                   cl::value_desc("N"));

static cl::opt<bool> TerminateLoop("sbt-loop-unroll-terminate",
                                    cl::desc("Terminate the paths that exceed the "
                                             "unrolling count."));


namespace {
  class LoopUnroll : public LoopPass {
    public:
      static char ID;

      LoopUnroll() : LoopPass(ID) {}

      bool runOnLoop(Loop *, LPPassManager&) override;
  };
}

static RegisterPass<LoopUnroll> SLU("sbt-loop-unroll",
                                    "Unroll loops in the program");
char LoopUnroll::ID;


bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);

static BasicBlock *createTerminatingBlock(Function *F,
                                          Instruction *I) {
  auto M = F->getParent();
  LLVMContext& Ctx = M->getContext();
  BasicBlock *block = BasicBlock::Create(Ctx, "loop_term");

  F->getBasicBlockList().push_back(block);

  auto assume = M->getOrInsertFunction("__VERIFIER_assume",
                                       Type::getVoidTy(Ctx),
                                       Type::getInt32Ty(Ctx)
#if LLVM_VERSION_MAJOR < 5
                                       , nullptr
#endif
                         );
  // The contents of the block is:
  //  __VERIFIER_assume(0)
  //  unreachable
  auto CI
    = CallInst::Create(assume, {ConstantInt::get(Type::getInt32Ty(Ctx), 0)},
                       "", block);
  new UnreachableInst(Ctx, block);

  // take the metadata from I, some passes would consider the module
  // broken without the metadata
  if (!CloneMetadata(I, CI)) {
      llvm::errs() << "[Unrolling] Failed assigning metadata to: " << *CI << "\n";
  }

  return block;
}

// redirect node successors
static void redirectEdges(const BasicBlock *origB,
                          BasicBlock *newB,
                          const std::map<BasicBlock *, BasicBlock *>& BlocksMap) {
  auto origTI = origB->getTerminator();
  auto newTI = newB->getTerminator();

  // copy the metadata from origTI,
  // some passes would consider the module
  // broken without the metadata
  if (!CloneMetadata(origTI, newTI)) {
      llvm::errs() << "[Unrolling] Failed assigning metadata to: " << *newTI << "\n";
  }

  for (unsigned i = 0; i < origTI->getNumSuccessors(); ++i) {
      auto it = BlocksMap.find(origTI->getSuccessor(i));
      if (it != BlocksMap.end()) {
        assert(it->second != nullptr);
        newTI->setSuccessor(i, it->second);
      }
  }
}

static void replaceSuccessor(const std::vector<BasicBlock *>& Blocks,
                             BasicBlock *oldB, BasicBlock *newB) {
  for (size_t i = 0; i < Blocks.size(); ++i) {
    auto origTI = Blocks[i]->getTerminator();
    for (unsigned i = 0; i < origTI->getNumSuccessors(); ++i) {
      auto succ = origTI->getSuccessor(i);
      // do we jump on the header?
      if (succ == oldB) {
          origTI->setSuccessor(i, newB);
      }
    }
  }
}

// redirect value uses and PHI nodes
static void redirectValues(BasicBlock *newB,
                           ValueToValueMapTy& VMap,
                           const std::map<BasicBlock *, BasicBlock *>& /*BlocksMap*/) {

  for (auto& I : *newB) {
    if (isa<PHINode>(&I)) {
      llvm::errs() << "PHI nodes are not supported yet\n";
      abort();
     //for (auto i = 0; i < PHI->getNumIncomingValues(); ++i) {
     //}
    } else {
      for (unsigned i = 0; i < I.getNumOperands(); ++i) {
        if (VMap.count(I.getOperand(i))) {
          I.setOperand(i, VMap[I.getOperand(i)]);
        }
      }
    }
  }
}

static std::vector<BasicBlock *>
cloneLoopBody(Function *F, const std::vector<BasicBlock *> Blocks) {

  ValueToValueMapTy VMap;
  std::map<BasicBlock *, BasicBlock *> BlocksMap;

  // clone the blocks
  std::vector<BasicBlock *> NewBlocks;
  NewBlocks.reserve(Blocks.size());
  for (auto Block : Blocks) {
    NewBlocks.push_back(CloneBasicBlock(Block, VMap));
    BlocksMap[Block] = NewBlocks.back();

    F->getBasicBlockList().push_back(NewBlocks.back());
  }

  // we got new basic blocks, now redirect the edges
  // and PHI values and such
  for (size_t i = 0; i < Blocks.size(); ++i) {
      redirectEdges(Blocks[i], NewBlocks[i], BlocksMap);
      redirectValues(NewBlocks[i], VMap, BlocksMap);
  }

  // reconnect the exit nodes from the old loop body
  // to the header of the new body
  replaceSuccessor(Blocks, Blocks[0], NewBlocks[0]);

  return NewBlocks;
}


bool LoopUnroll::runOnLoop(Loop *L, LPPassManager& /*LPM*/) {

  if (UnrollCount <= 1)
    return false;

  auto F = (*L->block_begin())->getParent();
  const auto& Blocks = L->getBlocks();

  std::vector<BasicBlock *> LastBlocks(Blocks.begin(), Blocks.end());
  // the code relies on the fact that the header is the first
  // basic block in the vector
  if (LastBlocks[0] != L->getHeader())
      abort();

  for (unsigned n = 1; n < UnrollCount; ++n)
      LastBlocks = cloneLoopBody(F, LastBlocks);

  // replace the next iterations with assume(false) if desired
  if (TerminateLoop) {
    auto termB = createTerminatingBlock(F, LastBlocks[0]->getTerminator());
    replaceSuccessor(LastBlocks, LastBlocks[0], termB);
  }

  return true;
}
