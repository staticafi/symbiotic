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
#include <llvm/IR/DebugInfoMetadata.h>
#include <llvm/Support/CommandLine.h>

using namespace llvm;

bool CloneMetadata(const llvm::Instruction *i1, llvm::Instruction *i2);

namespace {

llvm::cl::opt<bool> useExit("remove-error-calls-use-exit",
        llvm::cl::desc("Insert __VERIFIER_exit(0) instead of __VERIFIER_assume(0)\n"),
        llvm::cl::init(false));

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
  LLVMContext& Ctx = M->getContext();
  std::unique_ptr<CallInst> ext;

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;
    if (CallInst *CI = dyn_cast<CallInst>(ins)) {
      if (CI->isInlineAsm())
        continue;

#if LLVM_VERSION_MAJOR >= 8
      const Value *val = CI->getCalledOperand()->stripPointerCasts();
#else
      const Value *val = CI->getCalledValue()->stripPointerCasts();
#endif
      const Function *callee = dyn_cast<Function>(val);
      if (!callee || callee->isIntrinsic())
        continue;

      assert(callee->hasName());
      StringRef name = callee->getName();

      if (name.equals("__VERIFIER_error") ||
          name.equals("__assert_fail")) {
        if (!ext) {
          Type *argTy = Type::getInt32Ty(Ctx);
          auto extF
            = M->getOrInsertFunction(useExit ? "__VERIFIER_exit" :
                                               "__VERIFIER_assume",
                                     Type::getVoidTy(Ctx), argTy
#if LLVM_VERSION_MAJOR < 5
                                       , nullptr
#endif
                                       );

          std::vector<Value *> args = { ConstantInt::get(argTy, 0) };
          ext = std::unique_ptr<CallInst>(CallInst::Create(extF, args));
        }

        // This will insert __VERIFIER_assume(0), which just aborts the path
        // (if normal exit would be inserted, the tools would check leaks
        // -- this is just a silent exit)
        auto CI2 = ext->clone();
        CloneMetadata(CI, CI2);
        // insert also unreachable inst
        CI2->insertAfter(CI);
        CI->eraseFromParent();

        // The unreachable inst is already there since
        // the original instruction was aborting the program
        //auto UI = new UnreachableInst(Ctx, CI2);
        //CloneMetadata(CI, UI);

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
