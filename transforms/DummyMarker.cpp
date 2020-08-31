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

class DummyMarker : public FunctionPass {
  public:
    static char ID;

    DummyMarker() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool DummyMarker::runOnFunction(Function &F)
{
  bool modified = false;
  Module *M = F.getParent();
  LLVMContext& Ctx = M->getContext();

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;
    auto CI = dyn_cast<CallInst>(ins);
    if (!CI)
        continue;

#if LLVM_VERSION_MAJOR >= 8
    auto calledFun = dyn_cast<Function>(CI->getCalledOperand()->stripPointerCasts());
#else
    auto calledFun = dyn_cast<Function>(CI->getCalledValue()->stripPointerCasts());
#endif
    if (!calledFun)
        continue;
    auto fun = calledFun->getName();
    if (fun.equals("malloc") || fun.equals("calloc")) {
      auto dummyC = M->getOrInsertFunction("__symbiotic_keep_ptr",
                                           Type::getVoidTy(Ctx),
                                           Type::getInt8PtrTy(Ctx)
#if LLVM_VERSION_MAJOR < 5
                                           , nullptr
#endif
                                           );
#if LLVM_VERSION_MAJOR >= 9
      auto dummy = cast<Function>(dummyC.getCallee());
#else
      auto dummy = cast<Function>(dummyC);
#endif
      auto new_CI = CallInst::Create(dummy, {CI});
      CloneMetadata(CI, new_CI);

      new_CI->insertAfter(CI);
      modified = true;
    }
  }
  return modified;
}

} // namespace

static RegisterPass<DummyMarker> DM("dummy-marker",
                                    "Put calls to dummy functions into bitcode to "
                                    "prevent remove the code by optimizations.");
char DummyMarker::ID;
