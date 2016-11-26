//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
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
#include "llvm/IR/TypeBuilder.h"
#if (LLVM_VERSION_MINOR >= 5)
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

// FIXME: don't duplicate the code with -instrument-alloca
// replace CallInst with alloca with nondeterministic value
// TODO: what about pointers it takes as parameters?
static void replaceCall(CallInst *CI, Module *M)
{
  LLVMContext& Ctx = M->getContext();
  DataLayout *DL = new DataLayout(M->getDataLayout());
  Constant *name_init = ConstantDataArray::getString(Ctx, "nondet_from_undef");
  GlobalVariable *name = new GlobalVariable(*M, name_init->getType(), true, GlobalValue::PrivateLinkage, name_init);
  Type *size_t_Ty;

  if (DL->getPointerSizeInBits() > 32)
    size_t_Ty = Type::getInt64Ty(Ctx);
  else
    size_t_Ty = Type::getInt32Ty(Ctx);

  //void klee_make_symbolic(void *addr, size_t nbytes, const char *name);
  Constant *C = M->getOrInsertFunction("klee_make_symbolic",
                                       Type::getVoidTy(Ctx),
                                       Type::getInt8PtrTy(Ctx), // addr
                                       size_t_Ty,   // nbytes
                                       Type::getInt8PtrTy(Ctx), // name
                                       NULL);


  Type *Ty = CI->getType();
  // we checked for this before
  assert(!Ty->isVoidTy());
  // what to do in this case?
  assert(Ty->isSized());

  AllocaInst *AI = new AllocaInst(Ty, "alloca_from_undef");
  LoadInst *LI = new LoadInst(AI);
  CallInst *newCI = NULL;
  CastInst *CastI = NULL;

  std::vector<Value *> args;
  CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(Ctx));

  args.push_back(CastI);
  args.push_back(ConstantInt::get(size_t_Ty, DL->getTypeAllocSize(Ty)));
  args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));
  newCI = CallInst::Create(C, args);


  AI->insertAfter(CI);
  CastI->insertAfter(AI);
  newCI->insertAfter(CastI);
  LI->insertAfter(newCI);

  CI->replaceAllUsesWith(LI);
}

static const char *leave_calls[] = {
  "__assert_fail",
  "abort",
  "klee_make_symbolic",
  "klee_assume",
  "klee_abort",
  "klee_silent_exit",
  "klee_report_error",
  "klee_warning_once",
  "exit",
  "_exit",
  "malloc",
  "calloc",
  "realloc",
  "free",
  "memset",
  "memcmp",
  "memcpy",
  "memmove",
  "kzalloc",
  "__errno_location",
  NULL
};

static bool deleteUndefined(Function &F, bool nosym = false)
{
  // static set for the calls that we removed, so that
  // we can print those call only once
  static std::set<const llvm::Value *> removed_calls;
  bool modified = false;
  Module *M = F.getParent();

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

      if (name.equals("nondet_int") ||
          name.equals("klee_int") || array_match(name, leave_calls)) {
        continue;
      }

      // if this is __VERIFIER_something call different that to nondet,
      // keep it
      if (name.startswith("__VERIFIER") && !name.startswith("__VERIFIER_nondet"))
        continue;

      if (callee->isDeclaration()) {
        if (removed_calls.insert(callee).second) {
          // print only once
          errs() << "Prepare: removed calls to '" << name << "' (function is undefined";
          if (!CI->getType()->isVoidTy()) {
            if (nosym)
                errs() << ", retval set to 0)\n";
            else
                errs() << ", retval made symbolic)\n";
          } else
            errs() << ")\n";
        }

        if (!CI->getType()->isVoidTy()) {
          if (nosym) {
            // replace the return value with 0, since we don't want
            // to use the symbolic value
            CI->replaceAllUsesWith(Constant::getNullValue(CI->getType()));
          } else
            // replace the return value with symbolic value
            replaceCall(CI, M);
        }

        CI->eraseFromParent();
        modified = true;
      }
    }
  }
  return modified;
}

namespace {
  class DeleteUndefined : public FunctionPass {
    public:
      static char ID;

      DeleteUndefined() : FunctionPass(ID) {}

      virtual bool runOnFunction(Function &F)
      {
        return deleteUndefined(F);
      }
  };
}

static RegisterPass<DeleteUndefined> DLTU("delete-undefined",
                                          "delete calls to undefined functions, "
                                          "possible return value is made symbolic");
char DeleteUndefined::ID;

namespace {
  class DeleteUndefinedNoSym : public FunctionPass {
    public:
      static char ID;

      DeleteUndefinedNoSym() : FunctionPass(ID) {}

      virtual bool runOnFunction(Function &F)
      {
        return deleteUndefined(F, true /* no symbolic retval */);
      }
  };
}

static RegisterPass<DeleteUndefinedNoSym> DLTUNS("delete-undefined-nosym",
                                          "delete calls to undefined functions, "
                                          "possible return value is made 0");
char DeleteUndefinedNoSym::ID;

