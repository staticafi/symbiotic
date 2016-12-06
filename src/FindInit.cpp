//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>

#include "llvm/IR/Function.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/TypeBuilder.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

using namespace llvm;

// needed for the old slicer
namespace {
  class FindInit : public ModulePass {
    public:
      static char ID;

      FindInit() : ModulePass(ID) {}

      virtual bool runOnModule(Module &M)
      {
        findInitFuns(M);
        // we modified the module
        return true;
      }

    private:
      void findInitFuns(Module &M);
  };
}

void FindInit::findInitFuns(Module &M) {
  SmallVector<Constant *, 1> initFns;
  Type *ETy = TypeBuilder<void *, false>::get(M.getContext());
  Function *_main = M.getFunction("main");
  assert(_main);
  // for the case of NDEBUG
  if (!_main)
    abort();

  initFns.push_back(ConstantExpr::getBitCast(_main, ETy));
  ArrayType *ATy = ArrayType::get(ETy, initFns.size());
  new GlobalVariable(M, ATy, true, GlobalVariable::InternalLinkage,
                     ConstantArray::get(ATy, initFns),
                     "__ai_init_functions");
}

static RegisterPass<FindInit> FINIT("find-init",
                                    "[For the old slicer] Create a global variable and store pointer to main there");
char FindInit::ID;

