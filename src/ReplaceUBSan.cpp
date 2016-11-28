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
#include "llvm/IR/TypeBuilder.h"
#if (LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

using namespace llvm;

namespace {

class ReplaceUBSan : public FunctionPass {
  public:
    static char ID;

    ReplaceUBSan() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool ReplaceUBSan::runOnFunction(Function &F)
{
  bool modified = false;
  Module *M = F.getParent();
  Function *ver_err = nullptr;

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;
    if (CallInst *CI = dyn_cast<CallInst>(ins)) {
      if (CI->isInlineAsm())
        continue;

      const Value *val = CI->getCalledValue()->stripPointerCasts();
      const Function *callee = dyn_cast<Function>(val);
      if (!callee || callee->isIntrinsic())
        continue;

      assert(callee->hasName());
      StringRef name = callee->getName();

      if (!name.startswith("__ubsan_handle"))
        continue;

      if (callee->isDeclaration()) {
        if (!ver_err) {
          LLVMContext& Ctx = M->getContext();
          ver_err = cast<Function>(M->getOrInsertFunction("__VERIFIER_error",
                                                          Type::getVoidTy(Ctx),
                                                          nullptr));
        }

        auto CI2 = CallInst::Create(ver_err);
        CI2->insertAfter(CI);
        CI->eraseFromParent();

        modified = true;
      }
    }
  }
  return modified;
}

} // namespace

static RegisterPass<ReplaceUBSan> RUBS("replace-ubsan",
                                       "Replace ubsan calls with calls to __VERIFIER_error");
char ReplaceUBSan::ID;


namespace {

class RemoveErrorCalls : public FunctionPass {
  public:
    static char ID;

    RemoveErrorCalls() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool RemoveErrorCalls::runOnFunction(Function &F)
{
  bool modified = false;
  Module *M = F.getParent();
  std::unique_ptr<CallInst> ext;

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;
    if (CallInst *CI = dyn_cast<CallInst>(ins)) {
      if (CI->isInlineAsm())
        continue;

      const Value *val = CI->getCalledValue()->stripPointerCasts();
      const Function *callee = dyn_cast<Function>(val);
      if (!callee || callee->isIntrinsic())
        continue;

      assert(callee->hasName());
      StringRef name = callee->getName();

      if (name.equals("__VERIFIER_error")) {
        if (!ext) {
          LLVMContext& Ctx = M->getContext();
          Type *argTy = Type::getInt32Ty(Ctx);
          Function *extF
            = cast<Function>(M->getOrInsertFunction("exit",
                                                    Type::getVoidTy(Ctx),
                                                    argTy, nullptr));

          std::vector<Value *> args = { ConstantInt::get(argTy, 0) };
          ext = std::unique_ptr<CallInst>(CallInst::Create(extF, args));
        }

        auto CI2 = ext->clone();
        CI2->insertAfter(CI);
        CI->eraseFromParent();

        modified = true;
      } else if (name.equals("__VERIFIER_assert")) {
        CI->eraseFromParent();
        modified = true;
      }
    }
  }
  return modified;
}

} // namespace

static RegisterPass<RemoveErrorCalls> RERC("remove-error-calls",
                                           "Remove calls to __VERIFIER_error");
char RemoveErrorCalls::ID;

