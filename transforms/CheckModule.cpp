//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/GlobPattern.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

static cl::list<std::string> detect_calls("detect-calls",
                                          cl::desc("Detect calls to functions"),
                                          cl::value_desc("function name globs"),
                                          cl::CommaSeparated);

static cl::opt<bool> detect_atomics("detect-atomics",
                                    cl::desc("Detect atomic instructions"));

class CheckModule : public ModulePass {
public:
  static char ID;

  CheckModule() : ModulePass(ID) {}

  bool runOnModule(Module& M) override;
};

static RegisterPass<CheckModule> DLTU("check-module",
                                       "Check whether the module contains "
                                       "given features (e.g., calls to pthread funs).");
char CheckModule::ID;

static bool matches(StringRef name) {
  for (auto& glob : detect_calls) {
    if (cantFail(GlobPattern::create(glob)).match(name))
      return true;
  }
  return false;
}

bool CheckModule::runOnModule(Module& M) {
  for (auto& F : M) {
    // clang declares only the functions that the program uses
    if (!matches(F.getName()))
      continue;

    llvm::errs() << "Found function " << F.getName() << "\n";
    for (auto *U : F.users()) {
      auto *CI = dyn_cast<CallInst>(U);
      if (CI && CI->getDebugLoc()) {
        llvm::errs() << "Found call to function " << F.getName() << " at "
                     << CI->getDebugLoc().getLine() << ":"
                     << CI->getDebugLoc().getCol() << "\n";
      }
    }
  }

  if (detect_atomics) {
    for (auto& F : M) {
      for (auto& I : instructions(F)) {
        if (I.isAtomic()) {
          llvm::errs() << "Found atomic instruction\n";
          return false;
        }
      }
    }
  }

  return false;
}
