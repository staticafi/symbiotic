//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <set>
#include <stack>

#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/CFG.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_os_ostream.h"

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


