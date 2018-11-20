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

bool CloneMetadata(const llvm::Instruction *i1, llvm::Instruction *i2);

namespace {

class ReplaceLifetimeMarkers : public FunctionPass {
  public:
    static char ID;

    ReplaceLifetimeMarkers() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool ReplaceLifetimeMarkers::runOnFunction(Function &F)
{
  bool modified = false;
  Module *M = F.getParent();
  LLVMContext& Ctx = M->getContext();
  Constant *ver_scope_enter = M->getOrInsertFunction("__VERIFIER_scope_enter",
                                           Type::getVoidTy(Ctx),
                                           Type::getInt8PtrTy(Ctx), nullptr);
  Constant *ver_scope_leave = M->getOrInsertFunction("__VERIFIER_scope_leave",
                                           Type::getVoidTy(Ctx),
                                           Type::getInt8PtrTy(Ctx), nullptr);

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;
    if (IntrinsicInst *II = dyn_cast<IntrinsicInst>(ins)) {
      if (II->getIntrinsicID() != Intrinsic::lifetime_start &&
          II->getIntrinsicID() != Intrinsic::lifetime_end)
          continue;

        CallInst* CI = nullptr;
        if (II->getIntrinsicID() == Intrinsic::lifetime_start) {
            CI = CallInst::Create(ver_scope_enter, { II->getOperand(1) });
        } else if (II->getIntrinsicID() == Intrinsic::lifetime_end) {
            CI = CallInst::Create(ver_scope_leave, { II->getOperand(1) });
        }

        CloneMetadata(II, CI);

        CI->insertAfter(II);
        II->eraseFromParent();

        modified = true;
      }
  }
  return modified;
}

} // namespace

static RegisterPass<ReplaceLifetimeMarkers> RUBS("replace-lifetime-markers",
                                       "Replace lifetime markers with calls to __VERIFIER_scope_*");
char ReplaceLifetimeMarkers::ID;
