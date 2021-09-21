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
#include <llvm/Support/CommandLine.h>

using namespace llvm;

cl::opt<bool> no_change_assumes("no-change-assumes",
        cl::desc("Do not replace __VERIFIER_assume with __INSTR_check_assume\n"),
        cl::init(false));

cl::opt<bool> use_exit("use-exit",
        cl::desc("Use calls to __VERIFIER_exit() instead of to __VERIFIER_silent_exit\n"),
        cl::init(false));

bool CloneMetadata(const llvm::Instruction *i1, llvm::Instruction *i2);

namespace {

class FindExits : public FunctionPass {
  public:
    static char ID;

    FindExits() : FunctionPass(ID) {}

    bool runOnFunction(Function &F) override;
    bool processBlock(BasicBlock& B);
};

bool FindExits::runOnFunction(Function &F)
{
  bool modified = false;

  for (auto& B : F) {
      modified |= processBlock(B);
  }

  return modified;
}

bool FindExits::processBlock(BasicBlock& B) {
  bool modified = false;
  Module *M = B.getParent()->getParent();
  LLVMContext& Ctx = M->getContext();
  bool isMain = B.getParent()->getName().equals("main");

  Type *argTy = Type::getInt32Ty(Ctx);
  Function *exitF = nullptr;
  if (use_exit) {
    auto exitC = M->getOrInsertFunction("__VERIFIER_exit",
                                         Type::getVoidTy(Ctx), argTy
#if LLVM_VERSION_MAJOR < 5
                                         , nullptr
#endif
                                       );
#if LLVM_VERSION_MAJOR >= 9
    exitF = cast<Function>(exitC.getCallee());
#else
    exitF = cast<Function>(exitC);
#endif
  } else {
    auto exitC = M->getOrInsertFunction("__VERIFIER_silent_exit",
                                         Type::getVoidTy(Ctx), argTy
#if LLVM_VERSION_MAJOR < 5
                                         , nullptr
#endif
                                       );
#if LLVM_VERSION_MAJOR >= 9
    exitF = cast<Function>(exitC.getCallee());
#else
    exitF = cast<Function>(exitC);
#endif
  }
  exitF->addFnAttr(Attribute::NoReturn);

  if (succ_begin(&B) == succ_end(&B)) {
    auto& BI = B.back();
    if (isMain || !isa<ReturnInst>(&BI)) { // return inst does not abort the program
                                           // (unless in main) just returns to the caller
        auto new_CI = CallInst::Create(exitF, {ConstantInt::get(argTy, 0)});
        CloneMetadata(&BI, new_CI);
        new_CI->insertBefore(&BI);
        modified = true;
    }
  }

  if (no_change_assumes) {
    return modified;
  }

  // Change __VERIFIER_assume for __INSTR_check_assume,
  // as assume(0) is taken as non-terminating
  for (auto& I : B) {
    if (auto CI = dyn_cast<CallInst>(&I)) {
#if LLVM_VERSION_MAJOR >= 8
      auto calledFun = dyn_cast<Function>(CI->getCalledOperand()->stripPointerCasts());
#else
      auto calledFun = dyn_cast<Function>(CI->getCalledValue()->stripPointerCasts());
#endif
      if (!calledFun)
          continue;
      if (calledFun->getName().equals("__VERIFIER_assume")) {
        auto ICAC = M->getOrInsertFunction("__INSTR_check_assume",
                                           Type::getVoidTy(Ctx), argTy
#if LLVM_VERSION_MAJOR < 5
                                           , nullptr
#endif
                                       );
#if LLVM_VERSION_MAJOR >= 9
        auto ICA = cast<Function>(ICAC.getCallee());
#else
        auto ICA = cast<Function>(ICAC);
#endif

          CI->setCalledFunction(ICA);
          modified = true;
      }
    }
  }

  return modified;
}

} // namespace

static RegisterPass<FindExits> DM("find-exits",
                                  "Put calls to __VERIFIER_silent_exit into bitcode "
                                  "before any exit from the program.");
char FindExits::ID;
