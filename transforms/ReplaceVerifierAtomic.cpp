//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
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

#if LLVM_VERSION_MAJOR >= 4 || (LLVM_VERSION_MAJOR == 3 && LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif


using namespace llvm;

bool CloneMetadata(const llvm::Instruction *i1, llvm::Instruction *i2);

namespace {

class ReplaceVerifierAtomic : public ModulePass {
  public:
    static char ID;

    ReplaceVerifierAtomic() : ModulePass(ID) {}

    bool runOnModule(Module &M) override {
        bool changed = false;
        // nidhugg has a bug that incorrectly handles __VERIFIER_atomic_ functions
        // The only problem is in the name of the function,
        // so just rename it and use our implementations.
        auto func = M.getFunction("__VERIFIER_atomic_begin");
        if (func) {
            func->setName("__symbiotic_atomic_begin");
            changed = true;
        }
        func = M.getFunction("__VERIFIER_atomic_end");
        if (func) {
            func->setName("__symbiotic_atomic_end");
            changed = true;
        }
        return changed;
    }
};

static RegisterPass<ReplaceVerifierAtomic> RVA("replace-verifier-atomic",
                                               "Replace calls to verifier atomic with calls to pthread API");
char ReplaceVerifierAtomic::ID;
}
