//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.


#include "llvm/IR/DataLayout.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/IR/Type.h"
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

