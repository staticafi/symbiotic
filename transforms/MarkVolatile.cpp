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
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/TypeBuilder.h"
#if LLVM_VERSION_MAJOR >= 4 || (LLVM_VERSION_MAJOR == 3 && LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <llvm/IR/DebugInfoMetadata.h>

using namespace llvm;

namespace {

class MarkVolatile : public FunctionPass {
  public:
    static char ID;

    MarkVolatile() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool MarkVolatile::runOnFunction(Function &F)
{
  bool modified = false;
  LLVMContext& ctx = F.getParent()->getContext();

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E; ++I) {
    Instruction *ins = &*I;
    if (CallInst *CI = dyn_cast<CallInst>(ins)) {
      if (CI->isInlineAsm())
        continue;

      const Value *val = CI->getCalledValue()->stripPointerCasts();
      const Function *callee = dyn_cast<Function>(val);
      if (!callee || callee->isIntrinsic())
        continue;

      assert(callee->hasName());
      StringRef name = callee->getName();

      if (!name.startswith("__INSTR_mark_pointer"))
        continue;

      // we found a marked instruction, make it volatile
      // if it is store or load
      auto nextIt = I;
      ++nextIt;
      if (StoreInst *SI = dyn_cast<StoreInst>(&*nextIt)) {
          SI->setVolatile(true);
          modified = true;
      } else if (LoadInst *LI = dyn_cast<LoadInst>(&*nextIt)) {
          LI->setVolatile(true);
          modified = true;
      } else if (MemIntrinsic *MI = dyn_cast<MemIntrinsic>(&*nextIt)) {
          MI->setVolatile(ConstantInt::getTrue(ctx));
          modified = true;
      } else {
          errs() << "[Warning]: this marked instruction was not made volatile:\n";
          errs() << *nextIt << "\n";
      }
    }
  }
  return modified;
}

} // namespace

static RegisterPass<MarkVolatile> MVLTL("mark-volatile",
                                        "Make marked instructions as volatile");
char MarkVolatile::ID;

