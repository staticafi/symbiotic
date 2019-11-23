//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

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
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"

using namespace llvm;

class InstrumentNontermination : public LoopPass {
  bool checkFunction(Function *F);
  bool instrumentLoop(Loop *L);
  bool instrumentLoop(Loop *L, const std::set<llvm::Value *>& variables);

  llvm::Value *getOperand(llvm::Value *v) {
      if (isa<Constant>(v) ||
          isa<AllocaInst>(v) || isa<GlobalVariable>(v)) {
          return v;
      }
      return nullptr;
  }

  Function *_assert{nullptr};

  public:
    static char ID;

    InstrumentNontermination() : LoopPass(ID) {}

    bool runOnLoop(Loop *L, LPPassManager &LPM) override {
      // for now, we detect only nested loops
      if (L->getParentLoop()) {
          // run on non-nested loops for now
          return false;
      }

      return instrumentLoop(L);
    }
};

bool InstrumentNontermination::checkFunction(Function *F) {
  if (!F) // call via pointer
      return false;

  if (F->getName().equals("__VERIFIER_assume") ||
      F->getName().equals("__VERIFIER_assert"))
    return true;
  return false;
}

bool InstrumentNontermination::instrumentLoop(Loop *L) {
  std::set<llvm::Value *> usedValues;

  for (auto *block : L->blocks()) {
    // check that the loop reads and writes only to known
    // locations (allocas and global variables)
    for (auto& I : *block) {
      if (auto *CI = dyn_cast<CallInst>(&I)) {
          if (!checkFunction(CI->getCalledFunction())) {
            return false;
          }
      } else if (auto LI = dyn_cast<LoadInst>(&I)) {
        if (auto v = getOperand(LI->getPointerOperand())) {
          if (!isa<ConstantInt>(v)) {
            usedValues.insert(v);
          }
        } else {
          return false;
        }
      } else if (auto SI = dyn_cast<StoreInst>(&I)) {
        if (auto p = getOperand(SI->getPointerOperand())) {
          if (!isa<ConstantInt>(p)) {
            usedValues.insert(p);
          }
        } else {
          return false;
        }
      } else {
        if (I.mayReadOrWriteMemory()) {
          llvm::errs() << "WARNING: Unhandled instr: " << I << "\n";
          return false;
        }
      }
    }
  }

  return instrumentLoop(L, usedValues);
}


bool InstrumentNontermination::instrumentLoop(Loop *L, const std::set<llvm::Value *>& variables) {
  auto *header = L->getHeader();
  assert(header);

  // mapping of old to new ones
  std::map<Value *, Value *> mapping;

  // for each variable, create its copy in the header
  // and store the last recent value from the original
  // variable
  for (auto *v : variables) {
    //errs() << "INFO: variable: " << *v << "\n";
    Instruction *newVal = nullptr;
    if (auto *I = dyn_cast<Instruction>(v)) {
        newVal = I->clone();
        newVal->insertAfter(I);
    } else if (auto *G = dyn_cast<GlobalValue>(v)) {
        // create a new alloca that
        // is going to be inserted at the beginning of the header
        newVal = new AllocaInst(G->getType()->getContainedType(0)
#if (LLVM_VERSION_MAJOR >= 5)
        , G->getType()->getAddressSpace()
#endif
        ); 

        // puth the alloca on the beginning of the function
        newVal->insertBefore(header->getParent()->getBasicBlockList().front().getTerminator());
    } else {
      llvm::errs() << "ERROR: Unhandled copying: " << *v << "\n";
      return false;
    }

    assert(newVal);
    mapping[v] = newVal;
  }

  // store the state of variables at the loop head
  for (auto& it : mapping) {
    auto *LI = new LoadInst(it.first);
    auto *SI = new StoreInst(LI, it.second);

    header->getInstList().push_front(SI);
    header->getInstList().push_front(LI);
  }

  // compare the old and new values after the iteration of the loop
  for (auto I = pred_begin(header), E = pred_end(header); I != E; ++I) {
    auto *term = (*I)->getTerminator();

    // the state must be stored before any enter ofer,
    // but the assertions are inserted only before the
    // jumps that come from the loop
    if (!L->contains(*I))
      continue;

    // create an assertion that the values are not all the same
    // as the old values (if this assert fails, we found
    // a cycle in the state space)
    Instruction *lastCond = nullptr;
    for (auto& it : mapping) {
      auto *newVal = new LoadInst(it.first);
      auto *oldVal = new LoadInst(it.second);
      auto *cmp = new ICmpInst(ICmpInst::ICMP_EQ, newVal, oldVal);
      newVal->insertBefore(term);
      oldVal->insertBefore(term);
      cmp->insertBefore(term);

      if (lastCond) {
        assert(mapping.size() > 1); // we can get here only after 1 iteration
        auto *And = BinaryOperator::Create(Instruction::And, lastCond, cmp);
        And->insertBefore(term);
        lastCond = And;
      } else {
        lastCond = cmp;
      }
    }

    assert(lastCond);

    if (!_assert) {
      auto M = header->getParent()->getParent();
      auto& Ctx = M->getContext();
      auto F = M->getOrInsertFunction("__INSTR_check_nontermination",
                                      Type::getVoidTy(Ctx), // retval
                                      Type::getInt1Ty(Ctx)  // condition
#if LLVM_VERSION_MAJOR < 5
                                      , nullptr
#endif
                                      );
#if LLVM_VERSION_MAJOR >= 9
      _assert = cast<Function>(F.getCallee()->stripPointerCasts());
#else
      _assert = cast<Function>(F);
#endif
    }


    // insert the assertion that all the values are the same
    assert(_assert);
    auto *CI = CallInst::Create(_assert, {lastCond});
    CI->insertBefore(term);
  }

  llvm::errs() << "Instrumented a loop with non-termination checks\n";
  return true;
}


static RegisterPass<InstrumentNontermination> CL("instrument-nontermination",
                                                  "Insert trivial checks for state space cycles");
char InstrumentNontermination::ID;

