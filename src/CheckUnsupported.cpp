//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <assert.h>
#include <vector>

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
#if LLVM_VERSION_MAJOR >= 4 || (LLVM_VERSION_MAJOR == 3 && LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

using namespace llvm;

static bool array_match(StringRef &name, const char **array)
{
  for (const char **curr = array; *curr; curr++)
    if (name.equals(*curr))
      return true;
  return false;
}

// FIXME: use CommandLine
void check_unsupported(Function& F, const char **unsupported_calls)
{
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

      if (array_match(name, unsupported_calls)) {
        errs() << "CheckUnsupported: call to '" << name << "' is unsupported\n";
        errs().flush();
      }
    }
  }
}

class CheckUnsupported : public FunctionPass
{
  public:
    static char ID;

    CheckUnsupported() : FunctionPass(ID) {}
    virtual bool runOnFunction(Function &F);
};

bool CheckUnsupported::runOnFunction(Function &F) {
  static const char *unsupported_calls[] = {
    "__isnan",
    "__isnanf",
    "__isinf",
    "__isinff",
    "__isinfl",
    "__fpclassify",
    "__fpclassifyf",
    "__signbit",
    "__signbitf",
    "__finite",
    "__finite1",
    "__finitef",
    "fesetround",
    "round",
    "roundf",
    "roundl",
    "trunc",
    "truncf",
    "truncl",
    "modf",
    "modff",
    "modfl",
    "fmod",
    "fmodf",
    "fmodl",
    "fmin",
    "fminf",
    "fminl",
    "fmax",
    "fmaxf",
    "fmaxl",
    "fdim",
    "fdimf",
    "fdiml",
    "longjmp",
    "setjmp",
    // I do not know if this is problem with us or with
    // benchmarks, but until I found out,
    // skip benchmarks with this function
    "getopt32",
    nullptr
  };

  check_unsupported(F, unsupported_calls);
  return false;
}

static RegisterPass<CheckUnsupported> CHCK("check-unsupported",
                                           "check calls to unsupported functions for symbiotic");
char CheckUnsupported::ID;

class CheckConcurrency : public FunctionPass
{
  public:
    static char ID;

    CheckConcurrency() : FunctionPass(ID) {}
    virtual bool runOnFunction(Function &F);
};

bool CheckConcurrency::runOnFunction(Function &F) {
  static const char *unsupported_calls[] = {
    "pthread_create",
    // we check this before too, since slicer will remove it for sure,
    // making source code wrong
    "fesetround",
    NULL
  };

  check_unsupported(F, unsupported_calls);
  return false;
}

static RegisterPass<CheckConcurrency> CHCKC("check-concurr",
                                            "check calls to pthread_create for symbiotic");
char CheckConcurrency::ID;

