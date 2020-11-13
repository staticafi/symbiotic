//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.


#include <cassert>
#include <vector>
#include <set>

#include "llvm/IR/DataLayout.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/IR/Type.h"
#if LLVM_VERSION_MAJOR >= 4 || (LLVM_VERSION_MAJOR == 3 && LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

using namespace llvm;

class PropagateConstants : public FunctionPass {
  public:
    static char ID;

    PropagateConstants() : FunctionPass(ID) {}

    bool runOnFunction(Function &F) override;
};

static RegisterPass<PropagateConstants> PC("propagate-constants",
                                           "Propagate constants");
char PropagateConstants::ID;

bool mustAlias(Value *v1, Value *v2) {
  // TODO: use alias analysis here
  if (auto *I1 = dyn_cast<Instruction>(v1)) {
    if (auto *I2 = dyn_cast<Instruction>(v2)) {
      return I1->stripPointerCasts() == I2->stripPointerCasts();
    }
  }
  return false;
}

bool mayAlias(Value *v1, Value *v2) {
  // TODO: use alias analysis here
  if (auto *A1 = dyn_cast<AllocaInst>(v1->stripPointerCasts())) {
    if (auto *A2 = dyn_cast<AllocaInst>(v2->stripPointerCasts())) {
      return A1 == A2; // different allocas cannot alias
    }
  }

  return true;
}

bool mayModify(Instruction *I, AllocaInst *var) {
  // TODO: use alias analysis here
  if (!I->mayWriteToMemory())
    return false;

  if (auto *S = dyn_cast<StoreInst>(I)) {
    if (!mayAlias(S->getPointerOperand(), var)) {
      return false;
    }
  }

  // return true on all other cases to be safe
  return true;
}

bool replace(AllocaInst *var, Constant *C, Instruction* I) {
  // replace loads of var for C
  //llvm::errs() << "  -> Trying replace at " << *I << "\n";
  if (auto *L = dyn_cast<LoadInst>(I)) {
    if (mustAlias(L->getPointerOperand(), var)) {
      llvm::errs() << "Replacing "
                   << "  " << *L << " with " << "  " << *C << "\n";
      L->replaceAllUsesWith(C);
      // DONT erase it, we use it for getting the successors
      return true;
    }
  }

  return false;
}

template <typename Queue, typename Visited>
void queueSuccessors(Queue& queue, Visited& visited, Instruction *curI) {
  // queue.put(successors(l))
  auto *nextI = curI->getNextNonDebugInstruction();
  if (nextI) {
    if (visited.insert(nextI).second) {
      queue.insert(nextI);
    }
  } else {
    auto *blk = curI->getParent();

    for (auto *succ : successors(blk)) {
      auto firstI = succ->getFirstNonPHIOrDbg();
      if (visited.insert(firstI).second) {
        queue.insert(firstI);
      }
    }
  }
  //llvm::errs() << "Queue size: " << queue.size() << "\n";
}

bool propagate(Instruction& Loc, AllocaInst *var, Constant *C) {
  // llvm::errs() << "Propagate " << *C << " to " << *var << "\nstarting at " << Loc << "\n";
  bool changed = false;
  // NOTE: not very efficient implementation
  std::set<Instruction *> visited;
  std::set<Instruction *> queue;

  queueSuccessors(queue, visited, &Loc);

  while (!queue.empty()) {
    // l = queue.pop()
    auto it = queue.begin();
    auto *curI = *it;
    queue.erase(it);

    // replace(V, C, l)
    changed |= replace(var, C, curI);
    if (!mayModify(curI, var)) {
      queueSuccessors(queue, visited, curI);
    }
  }
  return changed;
}

static inline AllocaInst *getVar(Value *val) {
    // TODO: use pointer analysis here
    // TODO: handle globals too
    if (auto *A = dyn_cast<AllocaInst>(val->stripPointerCasts()))
      return A;
    return nullptr;
}

bool PropagateConstants::runOnFunction(Function &F)  {
  if (F.isDeclaration())
    return false;

  bool changed = false;
  for (auto& I : instructions(F)) {
    if (auto *S = dyn_cast<StoreInst>(&I)) {
      if (auto *C = dyn_cast<Constant>(S->getValueOperand())) {
        if (auto *var = getVar(S->getPointerOperand())) {
          changed |= propagate(I, var, C);
        }
      }
    }
  }
  return changed;
}

