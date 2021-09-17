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

class InstrumentAlloc : public FunctionPass {
  public:
    static char ID;

    InstrumentAlloc() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

static RegisterPass<InstrumentAlloc> INSTALLOC("instrument-alloc",
                                               "replace calls to malloc and calloc with our funs");
char InstrumentAlloc::ID;

class InstrumentAllocNeverFails : public FunctionPass {
  public:
    static char ID;

    InstrumentAllocNeverFails() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

static RegisterPass<InstrumentAllocNeverFails> INSTALLOCNF("instrument-alloc-nf",
                                                           "replace calls to malloc and calloc with our funs and assume that the"
                                                           "allocation never fail");
char InstrumentAllocNeverFails::ID;

static void replace_malloc(Module *M, CallInst *CI, bool never_fails)
{
  Value *C = nullptr;

  if (never_fails) {
    auto X = M->getOrInsertFunction("__VERIFIER_malloc0", CI->getType(),
                                    CI->getOperand(0)->getType()
#if LLVM_VERSION_MAJOR < 5
    , nullptr
#endif
    );
#if LLVM_VERSION_MAJOR >= 9
    C = X.getCallee();
#else
    C = X;
#endif
  } else {
    auto X = M->getOrInsertFunction("__VERIFIER_malloc", CI->getType(), CI->getOperand(0)->getType()
#if LLVM_VERSION_MAJOR < 5
    , nullptr
#endif
    );
#if LLVM_VERSION_MAJOR >= 9
    C = X.getCallee();
#else
    C = X;
#endif
  }

  assert(C);
  Function *Malloc = cast<Function>(C);

  std::vector<Value *> args;
  args.push_back(CI->getOperand(0));

  CallInst *new_CI = CallInst::Create(Malloc, args);

  SmallVector<std::pair<unsigned, MDNode *>, 8> metadata;
  CI->getAllMetadata(metadata);
  // copy the metadata
  for (auto& md : metadata)
    new_CI->setMetadata(md.first, md.second);
  // copy the attributes (like zeroext etc.)
  new_CI->setAttributes(CI->getAttributes());

  new_CI->insertBefore(CI);
  CI->replaceAllUsesWith(new_CI);
  CI->eraseFromParent();
}

static void replace_calloc(Module *M, CallInst *CI, bool never_fails)
{
  Value *C = nullptr;
  if (never_fails) {
    auto X = M->getOrInsertFunction("__VERIFIER_calloc0", CI->getType(), CI->getOperand(0)->getType(), CI->getOperand(1)->getType()
#if LLVM_VERSION_MAJOR < 5
    , nullptr
#endif
    );
#if LLVM_VERSION_MAJOR >= 9
    C = X.getCallee();
#else
    C = X;
#endif
  } else {
    auto X = M->getOrInsertFunction("__VERIFIER_calloc", CI->getType(), CI->getOperand(0)->getType(), CI->getOperand(1)->getType()
#if LLVM_VERSION_MAJOR < 5
    , nullptr
#endif
    );
#if LLVM_VERSION_MAJOR >= 9
    C = X.getCallee();
#else
    C = X;
#endif
  }

  assert(C);
  Function *Calloc = cast<Function>(C);

  std::vector<Value *> args;
  args.push_back(CI->getOperand(0));
  args.push_back(CI->getOperand(1));

  CallInst *new_CI = CallInst::Create(Calloc, args);

  SmallVector<std::pair<unsigned, MDNode *>, 8> metadata;
  CI->getAllMetadata(metadata);
  // copy the metadata
  for (auto& md : metadata)
    new_CI->setMetadata(md.first, md.second);
  // copy the attributes (like zeroext etc.)
  new_CI->setAttributes(CI->getAttributes());

  new_CI->insertBefore(CI);
  CI->replaceAllUsesWith(new_CI);
  CI->eraseFromParent();
}

static bool instrument_alloc(Function &F, bool never_fails)
{
  // do not run the initializer on __VERIFIER and __INSTR functions
  const auto& fname = F.getName();
  if (fname.startswith("__VERIFIER_") || fname.startswith("__INSTR_"))
    return false;

  bool modified = false;
  Module *M = F.getParent();

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

      if (name.equals("malloc")) {
        replace_malloc(M, CI, never_fails);
        modified = true;
      } else if (name.equals("calloc")) {
        replace_calloc(M, CI, never_fails);
        modified = true;
      }
    }
  }
  return modified;
}

bool InstrumentAlloc::runOnFunction(Function &F)
{
    return instrument_alloc(F, false /* never fails */);
}

bool InstrumentAllocNeverFails::runOnFunction(Function &F)
{
    return instrument_alloc(F, true /* never fails */);
}

