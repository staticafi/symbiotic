//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <set>

#include "llvm/IR/Constants.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_os_ostream.h"

using namespace llvm;

class RemoveConstantExprs : public ModulePass {
public:
  static char ID;

  RemoveConstantExprs() : ModulePass(ID) {}

  bool runOnModule(Module& M) override;
  bool runOnFunction(Function &F);
};

static RegisterPass<RemoveConstantExprs> RCE("remove-constant-exprs",
                                             "Transform constant exprs to instructions");
char RemoveConstantExprs::ID;

bool RemoveConstantExprs::runOnModule(Module& M) {
  bool changed = false;
  for(auto& F : M) {
    changed |= runOnFunction(F);
  }

  return changed;
}

static inline llvm::ConstantExpr *getCEOperand(llvm::Instruction& I) {
    for (auto& op : I.operands()) {
      if (auto *CE = dyn_cast<ConstantExpr>(&op)) {
          return CE;
      }
    }
    return nullptr;
}

template <typename Queue>
void queueCEInst(Queue& queue, llvm::Instruction& I) {
  if (auto *CE = getCEOperand(I)) {
    queue.insert(std::make_pair(&I, CE));
  }
}

bool RemoveConstantExprs::runOnFunction(Function &F) {
  using namespace llvm;

  std::set<std::pair<Instruction *, ConstantExpr*>> instsWithCE;

  for (auto& I : llvm::instructions(F)) {
      queueCEInst(instsWithCE, I);
  }

  bool changed = false;
  while (!instsWithCE.empty()) {
    // FIXME: this is not very efficient, but let's optimize later
    auto cur = instsWithCE.begin();
    auto *I = cur->first;
    auto *CE = cur->second;
    instsWithCE.erase(cur);

    // FIXME: HACK for slowbeast
    // if this CE is a cast of the function in function call, skip it
    // FIXME: make this configurable
    if (auto *Call = dyn_cast<CallInst>(I)) {
#if LLVM_VERSION_MAJOR >= 8
      if (Call->getCalledOperand() == CE)
#else
      if (Call->getCalledValue() == CE)
#endif
        continue;
    }
    auto *newI = CE->getAsInstruction();
    newI->insertBefore(I);
    I->replaceUsesOfWith(CE, newI);
    // the instruction may contain another CE
    queueCEInst(instsWithCE, *I);
    // the new instruction may contain CE
    queueCEInst(instsWithCE, *newI);

    changed = true;
  }

/* Does not hold with the HACK
#ifndef NDEBUG 
  for (auto& I : llvm::instructions(F)) {
      queueCEInst(instsWithCE, I);
  }
  assert(instsWithCE.empty() && "Did not reach fixpoint");
#endif
*/

  return changed;
}

