//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.


#include <set>

#include "llvm/IR/DataLayout.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Pass.h"
#include "llvm/IR/Type.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include "llvm/Support/CommandLine.h"

using namespace llvm;

static cl::list<std::string> calls("delete-call",
                                   cl::desc("Specify which calls of functions to delete"));
namespace {
  class DeleteFuns : public FunctionPass {
    public:
      static char ID;

      DeleteFuns() : FunctionPass(ID) {}

      bool runOnFunction(Function &F) override;

  };
}

static RegisterPass<DeleteFuns> PRP("delete-calls",
                                    "Delete (direct) calls of the given function");
char DeleteFuns::ID;

bool DeleteFuns::runOnFunction(Function &F) {
  bool changed = false;
  std::set<std::string> callsset{calls.begin(), calls.end()};

  for (auto &B : F) {
    for (auto it = B.begin(), et = B.end(); it != et;) {
      auto &I = *it++;
      auto *CI = dyn_cast<CallInst>(&I);
      if (!CI)
          continue;

#if LLVM_VERSION_MAJOR < 8
      auto *op = CI->getCalledValue()->stripPointerCasts();
#else
      auto *op = CI->getCalledOperand()->stripPointerCasts();
#endif

      auto *fun = dyn_cast<Function>(op);
      if (!fun)
          continue;

      if (callsset.find(fun->getName().str()) != callsset.end()) {
          // remove the instruction
          //llvm::errs() << "Deleting " << I << "\n";
          I.replaceAllUsesWith(UndefValue::get(I.getType()));
          I.eraseFromParent();
          changed = true;
      }
    }
  }

  return changed;
}


/*
namespace {
  class Prepare : public ModulePass {
    public:
      static char ID;

      Prepare() : ModulePass(ID) {}

      virtual bool runOnModule(Module &M);

      bool replace_ldv_calls(Module &M);
      bool replace_ldv_calls(Module& M, Function &F);
  };
}

static RegisterPass<Prepare> PRP("prepare",
                                 "Prepare the code for svcomp");
char Prepare::ID;

bool Prepare::runOnModule(Module &M) {
  bool changed = false;

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
      //errs() << "deleting " << toDel->getName() << '\n';
      toDel->deleteBody();
      changed = true;
    }
  }

  // prevent __VERIFIER_assert from inlining, it introduces
  // a weakness in our control dependence algorithm in some cases
  if (Function *F = M.getFunction("__VERIFIER_assert")) {
    F->addFnAttr(Attribute::NoInline);
    changed = true;
  }

  static const char *set_linkage[] = {
    "malloc",
    "calloc",
    "realloc",
    nullptr
  };

  // we want to use our definiton of malloc
  for (const char **curr = set_linkage; *curr; curr++) {
    Function *F = M.getFunction(*curr);
    if (F && !F->empty()) {
      errs() << "Making " << F->getName() << " private\n";
      F->setLinkage(GlobalValue::PrivateLinkage);
      changed = true;
    }
  }

  return changed;// | replace_ldv_calls(M);
}

bool Prepare::replace_ldv_calls(Module &M) {
  bool changed = false;

  for (auto& F : M) {
    const StringRef& name = F.getName();
    if (!name.startswith("ldv_"))
      continue;

    changed |= replace_ldv_calls(M, F);
  }

  return changed;
}

bool Prepare::replace_ldv_calls(Module& M, Function &F) {
  bool changed = false;
  const StringRef& name = F.getName();

  if (!name.equals("ldv_assume") && !name.equals("ldv_stop"))
    return false;

  LLVMContext& Ctx = M.getContext();

  for (auto I = F.use_begin(), E = F.use_end(); I != E; ++I) {
#if ((LLVM_VERSION_MAJOR == 3) && (LLVM_VERSION_MINOR < 5))
    Value *use = *I;
#else
    Value *use = I->getUser();
#endif

    if (CallInst *CI = dyn_cast<CallInst>(use)) {
      std::vector<Value *> args;
      Constant *new_func = nullptr;
      if (name.equals("ldv_assume")) {
        Type *argTy = Type::getInt32Ty(Ctx);
        new_func = M.getOrInsertFunction("__VERIFIER_assume", Type::getVoidTy(Ctx),
                                         argTy
#if LLVM_VERSION_MAJOR < 5
                                       , nullptr
#endif
                                       );

        args.push_back(CI->getOperand(0));
      } else if (name.equals("ldv_stop")) {
        Type *argTy = Type::getInt32Ty(Ctx);
        new_func = M.getOrInsertFunction("__VERIFIER_silent_exit", Type::getVoidTy(Ctx),
                                         argTy
#if LLVM_VERSION_MAJOR < 5
                                       , nullptr
#endif
                                       );

        args.push_back(ConstantInt::get(argTy, 0));
      }

      CallInst *new_CI = CallInst::Create(new_func, args);
      SmallVector<std::pair<unsigned, MDNode *>, 8> metadata;
      CI->getAllMetadata(metadata);
      // copy the metadata
      for (auto& md : metadata)
        new_CI->setMetadata(md.first, md.second);
      // copy the attributes (like zeroext etc.)
      new_CI->setAttributes(CI->getAttributes());

      new_CI->insertAfter(CI);
      CI->replaceAllUsesWith(new_CI);
      CI->eraseFromParent();
    }
  }

  return changed;
}
*/
