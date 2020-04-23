//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <set>

#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_os_ostream.h"

using namespace llvm;

static cl::opt<std::string> detect_calls("detect-calls",
                                         cl::desc("Detect calls to functions"),
                                         cl::value_desc("function name"));



class CheckModule : public ModulePass {
  bool has_pointer_call = false;
  bool detected_call = false;

public:
  static char ID;

  CheckModule() : ModulePass(ID) {}

  bool runOnModule(Module& M) override;
  void runOnFunction(Function &F);
};

static RegisterPass<CheckModule> DLTU("check-module",
                                       "Check whether the module contains "
                                       "given features (e.g., calls to pthread funs).");
char CheckModule::ID;

bool CheckModule::runOnModule(Module& M) {
  if (!detect_calls.empty()) {
    if (!M.getFunction(detect_calls)) {
      // the function is not even declared in the module,
      // so it cannot be called
      return false;
    }
  }

  for(auto& F : M) {
    runOnFunction(F);
  }

  if (detected_call) {
    llvm::errs() << "Found call to function " << detect_calls << "\n";
  }
  if (has_pointer_call) {
    // this means that the detect_calls _may_ be called
    llvm::errs() << "Found a call via pointer\n";
  }

  return false;
}

void CheckModule::runOnFunction(Function &F)
{
  using namespace llvm;
  for (auto& B : F) {
    for (auto& I : B) {
      if (auto *CI = dyn_cast<CallInst>(&I)) {
        auto F = CI->getCalledFunction();
        if (!F) {
            has_pointer_call = true;
        } else {
            if (F->getName().str() == detect_calls) {
                detected_call = true;
            }
        }
      }
    }
  }
}

