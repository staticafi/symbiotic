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
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <llvm/IR/DebugInfoMetadata.h>

using namespace llvm;

bool CloneMetadata(const llvm::Instruction *i1, llvm::Instruction *i2);

namespace {

llvm::cl::opt<bool> justRemove("replace-ubsan-just-remove",
        llvm::cl::desc("Just remove the UBSan checks instead of replacing them with error call\n"),
        llvm::cl::init(false));

llvm::cl::opt<bool> keepShifts("replace-ubsan-keep-shifts",
        llvm::cl::desc("Keep checks for shifts (i.e., replace them with error call, the rest of ubsan is removed"),
        llvm::cl::init(false));



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

      if (!name.startswith("__ubsan_handle"))
        continue;

      bool isshift = name.startswith("__ubsan_handle_shift");

      if (callee->isDeclaration()) {
        // just remove ?
        if (justRemove && (!keepShifts || !isshift)) {
          CI->eraseFromParent();
          modified = true;
          continue;
        }

        // replace
        if (!ver_err) {
          LLVMContext& Ctx = M->getContext();
          auto C = M->getOrInsertFunction("__VERIFIER_error",
                                          Type::getVoidTy(Ctx)
#if LLVM_VERSION_MAJOR < 5
                                          , nullptr
#endif
                                         );
#if LLVM_VERSION_MAJOR >= 9
          ver_err = cast<Function>(C.getCallee()->stripPointerCasts());
#else
          ver_err = cast<Function>(C);
#endif
        }

        auto CI2 = CallInst::Create(ver_err);
        CloneMetadata(CI, CI2);

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
