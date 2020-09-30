//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

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
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include "llvm/IR/DebugInfoMetadata.h"

#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"

llvm::cl::opt<bool> insertHeader("instrument-nontermination-mark-header",
        llvm::cl::desc("Insert a function that marks the header of the loop"),
        llvm::cl::init(false));

using namespace llvm;

bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);

class InstrumentNontermination : public LoopPass {
  bool checkInstruction(Instruction& I, std::set<llvm::Value *>& variables,
                        std::vector<llvm::Function *> callstack);
  bool checkFunction(Function *F, std::set<llvm::Value *>& variables,
                     std::vector<llvm::Function *> callstack);
  bool instrumentLoop(Loop *L);
  bool instrumentLoop(Loop *L, const std::set<llvm::Value *>& variables);
  bool instrumentEmptyLoop(Loop *L);

  bool checkOperand(llvm::Value *v,
                    std::set<llvm::Value *>& usedValues,
                    bool nestedCall) {
      if (isa<AllocaInst>(v)) {
          if (!nestedCall) {
            usedValues.insert(v); // we do not care about allocas from nested calls
          }
          return true;
      } else if (isa<GlobalVariable>(v)) {
          usedValues.insert(v);
          return true;
      }
      // check only after global, global is also constant
      if (isa<Constant>(v))
          return true;

      return false;
  }

  Function *_assert{nullptr};
  Function *_fail{nullptr};
  Function *_header{nullptr};

  Function *getHeaderFun(Module *M) {
    if (!_header) {
      auto& Ctx = M->getContext();
      auto F = M->getOrInsertFunction("__INSTR_check_nontermination_header",
                                      Type::getVoidTy(Ctx) // retval
#if LLVM_VERSION_MAJOR < 5
                                      , nullptr
#endif
                                      );
#if LLVM_VERSION_MAJOR >= 9
      _header = cast<Function>(F.getCallee()->stripPointerCasts());
#else
      _header = cast<Function>(F);
#endif
    }
    return _header;
  }

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

bool InstrumentNontermination::checkFunction(Function *F,
                                             std::set<llvm::Value *>& usedValues,
                                             std::vector<llvm::Function *> callstack) {
  if (!F) // call via pointer
      return false;

  if (F->getName().equals("__VERIFIER_assume") ||
      F->getName().equals("__VERIFIER_assert") ||
      F->getName().startswith("__VERIFIER_nondet_") ||
      F->getName().startswith("__VERIFIER_exit") ||
      F->getName().startswith("__VERIFIER_silent_exit") ||
      F->getName().startswith("exit") ||
      F->getName().startswith("_exit") ||
      F->getName().startswith("abort") ||
      F->getName().startswith("klee_silent_exit") ||
      F->getName().startswith("llvm.dbg."))
    return true;

  for (auto *onstack : callstack) {
      if (onstack == F) {
          return false; // recursion
      }
  }

  callstack.push_back(F);

  for (auto& B : *F) {
    for (auto& I : B) {
      if (!checkInstruction(I, usedValues, callstack)) {
        return false;
      }
    }
  }

  return true;
}

bool InstrumentNontermination::instrumentLoop(Loop *L) {
  std::set<llvm::Value *> usedValues;

  for (auto *block : L->blocks()) {
    // check that the loop reads and writes only to known
    // locations (allocas and global variables)
    for (auto& I : *block) {
      // hmm... could be implemented more efficiently,
      // but it should be quite fast even though.
      if (!checkInstruction(I, usedValues, {})) {
        return false;
      }
    }
  }

  // all ok
  return instrumentLoop(L, usedValues);
}

bool InstrumentNontermination::checkInstruction(Instruction& I,
                                                std::set<llvm::Value*>& usedValues,
                                                std::vector<llvm::Function *> callstack) {
  bool isNested = !callstack.empty();
  //llvm::errs() << "checking (" << isNested << "): " << I << "\n";

  if (auto *CI = dyn_cast<CallInst>(&I)) {
    if (!checkFunction(CI->getCalledFunction(), usedValues, callstack)) {
      return false;
    }
  } else if (auto LI = dyn_cast<LoadInst>(&I)) {
    if (!checkOperand(LI->getPointerOperand(), usedValues, isNested)) {
      return false;
    }
  } else if (auto SI = dyn_cast<StoreInst>(&I)) {
    if (!checkOperand(SI->getPointerOperand(), usedValues, isNested)) {
      return false;
    }
  } else {
    if (I.mayReadOrWriteMemory()) {
      llvm::errs() << "WARNING: Unhandled instr: " << I << "\n";
      return false;
    }
  }

  return true;
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
        newVal = new AllocaInst(
            G->getType()->getContainedType(0),
#if (LLVM_VERSION_MAJOR >= 5)
            G->getType()->getAddressSpace(),
#endif
            nullptr,
            "",
            // put the alloca on the beginning of the function
            header->getParent()->getBasicBlockList().front().getTerminator());
    } else {
      llvm::errs() << "ERROR: Unhandled copying: " << *v << "\n";
      return false;
    }

    assert(newVal);
    mapping[v] = newVal;
  }

  if (mapping.empty()) {
      return instrumentEmptyLoop(L);
  }

  // store the state of variables at the loop head
  for (auto& it : mapping) {
    auto *LI = new LoadInst(
        it.first->getType()->getPointerElementType(),
        it.first,
        "",
#if LLVM_VERSION_MAJOR >= 11
        false,
        header->getModule()->getDataLayout()
            .getABITypeAlign(it.first->getType()),
#endif
        static_cast<Instruction*>(nullptr));
    auto *SI = new StoreInst(LI,
        it.second,
        false,
#if LLVM_VERSION_MAJOR >= 11
        LI->getAlign(),
#endif
        static_cast<Instruction*>(nullptr));

    CloneMetadata(header->getTerminator(), LI);
    CloneMetadata(header->getTerminator(), SI);

    auto where = header->getFirstNonPHIOrDbg();
    assert(where);

    if (where == header->getTerminator()) {
      header->getInstList().push_front(SI);
      header->getInstList().push_front(LI);
    } else {
      LI->insertAfter(where);
      SI->insertAfter(LI);
    }

    if (insertHeader) {
        auto h = getHeaderFun(header->getParent()->getParent());
        auto *CI = CallInst::Create(_header);
        // copy the location from terminator, so that we have
        // the right debug loc
        CloneMetadata(header->getTerminator(), CI);
        CI->insertBefore(header->getTerminator());
    }
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
      auto *newVal = new LoadInst(
          it.first->getType()->getPointerElementType(),
          it.first,
          "",
          term);
      auto *oldVal = new LoadInst(
          it.second->getType()->getPointerElementType(),
          it.second,
          "",
          term);
      auto *cmp = new ICmpInst(ICmpInst::ICMP_EQ, newVal, oldVal);

#if LLVM_VERSION_MAJOR > 7
      auto md = term->getPrevNonDebugInstruction();
      if (!md || !md->hasMetadata())
          md = term;
#else
      auto md = term;
#endif
      CloneMetadata(md, newVal);
      CloneMetadata(md, oldVal);
      CloneMetadata(md, cmp);
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
    if (lastCond->hasMetadata())
      CloneMetadata(lastCond, CI);
    else
      CloneMetadata(term, CI);
    CI->insertBefore(term);
  }

  llvm::errs() << "Instrumented a loop with non-termination checks\n";
  return true;
}

bool InstrumentNontermination::instrumentEmptyLoop(Loop *L) {
  auto *header = L->getHeader();

  // go after unique successors and if you get to a loop,
  // we know this loop does not terminate
  // (since it passed our checks and it does not use any
  // variables, we know it may not terminate even from
  // some call)

  /* NOTE: this check is redundant:
   * after all the check we did, this must be potentionally
   * non-terminating. It may not be syntactically non-terminating,
   * it can be something like:
   *
   * while(nondet_bool())
   * {}
   *
   * But since it does not changes memory and calls
   * only functions without side-effects (or nondet()),
   * we know that there exist a cycle in the state space
  std::set<BasicBlock *> visited;
  visited.insert(header);
  auto *cur = header;
  do {
    cur = cur->getUniqueSuccessor();
    if (!cur) // no loop
        return false;

    assert(L->contains(cur));
    if (!visited.insert(cur).second) {
        // hit a cycle
        break;
    }
  } while (true);
  */

  // it is an infinite loop
  auto M = header->getParent()->getParent();
  auto& Ctx = M->getContext();
  if (!_fail) {
    auto F = M->getOrInsertFunction("__INSTR_fail",
                                    Type::getVoidTy(Ctx) // retval
#if LLVM_VERSION_MAJOR < 5
                                    , nullptr
#endif
                                    );
#if LLVM_VERSION_MAJOR >= 9
    _fail = cast<Function>(F.getCallee()->stripPointerCasts());
#else
    _fail = cast<Function>(F);
#endif
    _fail->setDoesNotReturn();
  }

  assert(_fail);
  for (auto I = pred_begin(header), E = pred_end(header); I != E; ++I) {
    auto *term = (*I)->getTerminator();
    auto *CI = CallInst::Create(_fail);
    CloneMetadata(term, CI);
    CI->insertBefore(term);
  }

  llvm::errs() << "Instrumented an empty loop with abort.\n";
  return true;
}

static RegisterPass<InstrumentNontermination> CL("instrument-nontermination",
                                                  "Insert trivial checks for state space cycles");
char InstrumentNontermination::ID;

