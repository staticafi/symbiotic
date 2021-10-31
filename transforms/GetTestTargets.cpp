//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <set>
#include <stack>

#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/CFG.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_os_ostream.h"
#include "llvm/Support/CommandLine.h"

using namespace llvm;

class GetTestTargets : public ModulePass {
public:
  static char ID;

  GetTestTargets() : ModulePass(ID) {}

  bool runOnModule(Module& M) override;
};

bool CloneMetadata(const llvm::Instruction *i1, llvm::Instruction *i2);

static RegisterPass<GetTestTargets> GTT("get-test-targets",
                                       "Find targets for tests generation");
char GetTestTargets::ID;

bool GetTestTargets::runOnModule(Module& M) {
    bool changed = false;
    std::set<BasicBlock*> visited;
    std::stack<BasicBlock*> queue; // not efficient...
    auto& Ctx = M.getContext();
    unsigned n = 0;

    auto *mf = M.getFunction("main");
    if (!mf)
        return false;
    queue.push(&mf->getEntryBlock());

    while (!queue.empty()) {
        auto *cur = queue.top();
        queue.pop();

        bool has_call = false;
        for (auto& I : *cur) {
          if (auto *C = dyn_cast<CallInst>(&I)) {
            if (auto *F = C->getCalledFunction()) {
              if (!F->isDeclaration()) {
                has_call = true;
                auto *entry = &F->getEntryBlock();
                if (visited.insert(entry).second)
                  queue.push(entry);
              }
            }
          }
        }

        if ((succ_begin(cur) == succ_end(cur)) && !has_call) {
          // generate slicing criterion
          std::string name = "__SYMBIOTIC_test_target" + std::to_string(n++);
          auto funC = M.getOrInsertFunction(name,
                                            Type::getVoidTy(Ctx)
#if LLVM_VERSION_MAJOR < 5
                                            , nullptr
#endif
                                            );
#if LLVM_VERSION_MAJOR >= 9
          auto *fun = cast<Function>(funC.getCallee());
#else
          auto *fun = cast<Function>(funC);
#endif
          auto new_CI = CallInst::Create(fun);
          auto *point = cur->getFirstNonPHI();
          CloneMetadata(point, new_CI);
          new_CI->insertBefore(point);

          changed = true;
          llvm::outs() << name << "\n";
        } else {
          for (auto *succ : successors(cur)) {
            if (visited.insert(succ).second)
              queue.push(succ);
          }
        }
    }


  return changed;
}


class ConstraintToTarget : public ModulePass {
public:
  static char ID;

  ConstraintToTarget() : ModulePass(ID) {}

  bool runOnModule(Module& M) override;
};


static cl::opt<std::string> TheTarget("ctt-target",
        llvm::cl::desc("Constraint the program to the target\n"));

static RegisterPass<ConstraintToTarget> CTT("constraint-to-target",
                                       "Find targets for tests generation");

char ConstraintToTarget::ID;

bool ConstraintToTarget::runOnModule(Module& M) {
    bool changed = false;
    std::set<BasicBlock*> relevant;
    std::set<BasicBlock*> visited;
    std::stack<BasicBlock*> queue; // not efficient...
    auto& Ctx = M.getContext();

    auto *mf = M.getFunction(TheTarget);
    if (!mf) {
        llvm::errs() << "ERROR: did not find the target" << TheTarget << "\n";
        return false;
    }

    for (auto use_it = mf->use_begin(), use_end = mf->use_end();
         use_it != use_end; ++use_it) {
#if ((LLVM_VERSION_MAJOR == 3) && (LLVM_VERSION_MINOR < 5))
      CallInst *CI = dyn_cast<CallInst>(*use_it);
#else
      CallInst *CI = dyn_cast<CallInst>(use_it->getUser());
#endif
      if (CI) {
        if (visited.insert(CI->getParent()).second)
          queue.push(CI->getParent());
      }
    }

    while (!queue.empty()) {
        auto *cur = queue.top();
        queue.pop();

        // paths from this block go to the target
        relevant.insert(cur);

        if ((pred_begin(cur) == pred_end(cur))) {
          // pop-up from call
          auto *fun = cur->getParent();
          for (auto use_it = fun->use_begin(), use_end = fun->use_end();
               use_it != use_end; ++use_it) {
#if ((LLVM_VERSION_MAJOR == 3) && (LLVM_VERSION_MINOR < 5))
            CallInst *CI = dyn_cast<CallInst>(*use_it);
#else
            CallInst *CI = dyn_cast<CallInst>(use_it->getUser());
#endif
            if (CI) {
              if (visited.insert(CI->getParent()).second)
                queue.push(CI->getParent());
            }
          }
        } else {
          for (auto *pred : predecessors(cur)) {
            if (visited.insert(pred).second)
              queue.push(pred);
          }
        }
    }

    if (relevant.empty()) {
      llvm::errs() << "Found no relevant blocks\n";
      return false;
    }

    Type *argTy = Type::getInt32Ty(Ctx);
    auto exitC = M.getOrInsertFunction("__VERIFIER_silent_exit",
                                       Type::getVoidTy(Ctx), argTy
#if LLVM_VERSION_MAJOR < 5
                                   , nullptr
#endif
                                   );
#if LLVM_VERSION_MAJOR >= 9
    auto exitF = cast<Function>(exitC.getCallee());
#else
    auto exitF = cast<Function>(exitC);
#endif
    exitF->addFnAttr(Attribute::NoReturn);

    for (auto& F : M) {
      for (auto& B : F) {
        if (relevant.count(&B) == 0) {
          auto new_CI = CallInst::Create(exitF, {ConstantInt::get(argTy, 0)});
          auto *point = B.getFirstNonPHI();
          CloneMetadata(point, new_CI);
          new_CI->insertBefore(point);
          changed = true;
        }
      }
    }

  return changed;
}



