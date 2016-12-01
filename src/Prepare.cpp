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
  class Prepare : public ModulePass {
    public:
      static char ID;

      Prepare() : ModulePass(ID) {}

      virtual bool runOnModule(Module &M);
  };
}

static RegisterPass<Prepare> PRP("prepare",
                                 "Prepare the code for svcomp");
char Prepare::ID;

bool Prepare::runOnModule(Module &M) {
  static const char *del_body[] = {
    "__VERIFIER_assume",
    "__VERIFIER_error",
    "__VERIFIER_nondet_pointer",
    "__VERIFIER_nondet_pchar",
    "__VERIFIER_nondet_char",
    "__VERIFIER_nondet_short",
    "__VERIFIER_nondet_int",
    "__VERIFIER_nondet_long",
    "__VERIFIER_nondet_uchar",
    "__VERIFIER_nondet_ushort",
    "__VERIFIER_nondet_uint",
    "__VERIFIER_nondet_ulong",
    "__VERIFIER_nondet_unsigned",
    "__VERIFIER_nondet_u32",
    "__VERIFIER_nondet_float",
    "__VERIFIER_nondet_double",
    "__VERIFIER_nondet_bool",
    "__VERIFIER_nondet__Bool",
    "__VERIFIER_nondet_size_t",
    nullptr
  };

  for (const char **curr = del_body; *curr; curr++) {
    Function *toDel = M.getFunction(*curr);
    if (toDel && !toDel->empty()) {
      errs() << "deleting " << toDel->getName() << '\n';
      toDel->deleteBody();
    }
  }

  // prevent __VERIFIER_assert from inlining, it introduces
  // a weakness in our control dependence algorithm in some cases
  if (Function *F = M.getFunction("__VERIFIER_assert"))
    F->addFnAttr(Attribute::NoInline);

  return true;
}

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
  Constant *C = NULL;

  if (never_fails)
    C = M->getOrInsertFunction("__VERIFIER_malloc0", CI->getType(), CI->getOperand(0)->getType(), NULL);
  else
    C = M->getOrInsertFunction("__VERIFIER_malloc", CI->getType(), CI->getOperand(0)->getType(), NULL);

  assert(C);
  Function *Malloc = cast<Function>(C);

  CI->setCalledFunction(Malloc);
}

static void replace_calloc(Module *M, CallInst *CI, bool never_fails)
{
  Constant *C = NULL;
  if (never_fails)
    C = M->getOrInsertFunction("__VERIFIER_calloc0", CI->getType(), CI->getOperand(0)->getType(), CI->getOperand(1)->getType(), NULL);
  else
    C = M->getOrInsertFunction("__VERIFIER_calloc", CI->getType(), CI->getOperand(0)->getType(), CI->getOperand(1)->getType(), NULL);

  assert(C);
  Function *Calloc = cast<Function>(C);
  CI->setCalledFunction(Calloc);
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

      const Value *val = CI->getCalledValue()->stripPointerCasts();
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

