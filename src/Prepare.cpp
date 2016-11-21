//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <assert.h>
#include <cstring>
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

// FIXME: use CommandLine
void check_unsupported(Function& F, const char **unsupported_calls)
{
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

      if (array_match(name, unsupported_calls)) {
        errs() << "CheckUnsupported: call to '" << name << "' is unsupported\n";
        errs().flush();
      }
    }
  }
}

class CheckUnsupported : public FunctionPass
{
  public:
    static char ID;

    CheckUnsupported() : FunctionPass(ID) {}
    virtual bool runOnFunction(Function &F);
};

bool CheckUnsupported::runOnFunction(Function &F) {
  static const char *unsupported_calls[] = {
    "__isnan",
    "__isnanf",
    "__isinf",
    "__isinff",
    "__isinfl",
    "__fpclassify",
    "__fpclassifyf",
    "__signbit",
    "__signbitf",
    "fesetround",
    "round",
    "roundf",
    "roundl",
    "trunc",
    "truncf",
    "truncl",
    "modf",
    "modff",
    "modfl",
    "fmod",
    "fmodf",
    "fmodl",
    "fmin",
    "fminf",
    "fminl",
    "fmax",
    "fmaxf",
    "fmaxl",
    "fdim",
    "fdimf",
    "fdiml",
    NULL
  };

  check_unsupported(F, unsupported_calls);
  return false;
}

static RegisterPass<CheckUnsupported> CHCK("check-unsupported",
                                           "check calls to unsupported functions for symbiotic");
char CheckUnsupported::ID;

class CheckConcurrency : public FunctionPass
{
  public:
    static char ID;

    CheckConcurrency() : FunctionPass(ID) {}
    virtual bool runOnFunction(Function &F);
};

bool CheckConcurrency::runOnFunction(Function &F) {
  static const char *unsupported_calls[] = {
    "pthread_create",
    // we check this before too, since slicer will remove it for sure,
    // making source code wrong
    "fesetround",
    NULL
  };

  check_unsupported(F, unsupported_calls);
  return false;
}

static RegisterPass<CheckConcurrency> CHCKC("check-concurr",
                                            "check calls to pthread_create for symbiotic");
char CheckConcurrency::ID;

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
/*
  "sprintf",
  "snprintf",
  "swprintf",
*/
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
  LLVMContext &C = M.getContext();

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

  for (Module::global_iterator I = M.global_begin(), E = M.global_end();
      I != E; ++I) {
    GlobalVariable *GV = &*I;
    if (GV->isConstant() || GV->hasInitializer())
      continue;
    GV->setInitializer(Constant::getNullValue(GV->getType()->getElementType()));
    errs() << "making " << GV->getName() << " non-extern\n";
  }

  return true;
}

class InstrumentAlloc : public FunctionPass {
  public:
    static char ID;

    InstrumentAlloc() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

static RegisterPass<InstrumentAlloc> INSTALLOC("instrument-alloc",
                                               "replace calls to malloc and calloc with our funs");
char InstrumentAlloc::ID;

class InstrumentAllocNeverFails : public FunctionPass {
  public:
    static char ID;

    InstrumentAllocNeverFails() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

static RegisterPass<InstrumentAllocNeverFails> INSTALLOCNF("instrument-alloc-nf",
                                                           "replace calls to malloc and calloc with our funs and assume that the"
                                                           "allocation never fail");
char InstrumentAllocNeverFails::ID;

static void replace_malloc(Module *M, CallInst *CI, bool never_fails)
{
  Constant *C = NULL;

  if (never_fails)
    C = M->getOrInsertFunction("__VERIFIER_malloc0", CI->getType(), CI->getOperand(0)->getType(), NULL);
  else
    C = M->getOrInsertFunction("__VERIFIER_malloc", CI->getType(), CI->getOperand(0)->getType(), NULL);

  assert(C);
  Function *Malloc = cast<Function>(C);

  CI->setCalledFunction(Malloc);
}

static void replace_calloc(Module *M, CallInst *CI, bool never_fails)
{
  Constant *C = NULL;
  if (never_fails)
    C = M->getOrInsertFunction("__VERIFIER_calloc0", CI->getType(), CI->getOperand(0)->getType(), CI->getOperand(1)->getType(), NULL);
  else
    C = M->getOrInsertFunction("__VERIFIER_calloc", CI->getType(), CI->getOperand(0)->getType(), CI->getOperand(1)->getType(), NULL);

  assert(C);
  Function *Calloc = cast<Function>(C);
  CI->setCalledFunction(Calloc);
}

static bool instrument_alloc(Function &F, bool never_fails)
{
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

      if (name.equals("malloc")) {
        replace_malloc(M, CI, never_fails);
        modified = true;
      } else if (name.equals("calloc")) {
        replace_calloc(M, CI, never_fails);
        modified = true;
      }
    }
  }
  return modified;
}

bool InstrumentAlloc::runOnFunction(Function &F)
{
    return instrument_alloc(F, false /* never fails */);
}

bool InstrumentAllocNeverFails::runOnFunction(Function &F)
{
    return instrument_alloc(F, true /* never fails */);
}

class InitializeUninitialized : public FunctionPass {
  public:
    static char ID;

    InitializeUninitialized() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};


static RegisterPass<InitializeUninitialized> INIUNINI("initialize-uninitialized",
                                                      "initialize all uninitialized variables to non-deterministic value");
char InitializeUninitialized::ID;

bool InitializeUninitialized::runOnFunction(Function &F)
{
  bool modified = false;
  Module *M = F.getParent();
  LLVMContext& Ctx = M->getContext();
  DataLayout *DL = new DataLayout(M->getDataLayout());
  Constant *name_init = ConstantDataArray::getString(Ctx, "nondet");
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


  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;

    if (AllocaInst *AI = dyn_cast<AllocaInst>(ins)) {
      Type *Ty = AI->getAllocatedType();
      AllocaInst *newAlloca = NULL;
      CallInst *CI = NULL;
      CastInst *CastI = NULL;
      StoreInst *SI = NULL;
      LoadInst *LI = NULL;

      std::vector<Value *> args;

      // create new allocainst, declare it symbolic and store it
      // to the original alloca. This way slicer will slice this
      // initialization away if program initialize it manually later
      if (Ty->isSized()) {
        // if this is an array allocation, just call klee_make_symbolic on it,
        // since storing whole symbolic array into it would have soo huge overhead
        if (Ty->isArrayTy()) {
            CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(Ctx));
            args.push_back(CastI);
            args.push_back(ConstantInt::get(size_t_Ty, DL->getTypeAllocSize(Ty)));
            args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));

            CI = CallInst::Create(C, args);
            CastI->insertAfter(AI);
            CI->insertAfter(CastI);
        } else {
            // when this is not an array allocation, create new symbolic memory and
            // store it into the allocated memory using normal StoreInst.
            // That will allow slice away more unneeded allocations
            newAlloca = new AllocaInst(Ty, "alloca_uninitial");
            CastI = CastInst::CreatePointerCast(newAlloca, Type::getInt8PtrTy(Ctx));

            args.push_back(CastI);
            args.push_back(ConstantInt::get(size_t_Ty, DL->getTypeAllocSize(Ty)));
            args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));
            CI = CallInst::Create(C, args);

            LI = new LoadInst(newAlloca);
            SI = new StoreInst(LI, AI);

            newAlloca->insertAfter(AI);
            CastI->insertAfter(newAlloca);
            CI->insertAfter(CastI);
            LI->insertAfter(CI);
            SI->insertAfter(LI);
        }

        modified = true;
      }
    }
  }

  delete DL;
  return modified;
}

namespace {

class ReplaceUBSan : public FunctionPass {
  public:
    static char ID;

    ReplaceUBSan() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool ReplaceUBSan::runOnFunction(Function &F)
{
  bool modified = false;
  Module *M = F.getParent();
  Function *ver_err = nullptr;

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

      if (!name.startswith("__ubsan_handle"))
        continue;

      if (callee->isDeclaration()) {
        if (!ver_err) {
          LLVMContext& Ctx = M->getContext();
          ver_err = cast<Function>(M->getOrInsertFunction("__VERIFIER_error",
                                                          Type::getVoidTy(Ctx),
                                                          nullptr));
        }

        auto CI2 = CallInst::Create(ver_err);
        CI2->insertAfter(CI);
        CI->eraseFromParent();

        modified = true;
      }
    }
  }
  return modified;
}

} // namespace

static RegisterPass<ReplaceUBSan> RUBS("replace-ubsan",
                                       "Replace ubsan calls with calls to __VERIFIER_error");
char ReplaceUBSan::ID;


namespace {

class RemoveErrorCalls : public FunctionPass {
  public:
    static char ID;

    RemoveErrorCalls() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F);
};

bool RemoveErrorCalls::runOnFunction(Function &F)
{
  bool modified = false;
  Module *M = F.getParent();
  Function *ext = nullptr;

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

      if (name.equals("__VERIFIER_error")) {
        if (!ext) {
          LLVMContext& Ctx = M->getContext();
          ext = cast<Function>(M->getOrInsertFunction("exit",
                                                       Type::getInt32Ty(Ctx),
                                                       nullptr));
        }

        auto CI2 = CallInst::Create(ext);
        CI2->insertAfter(CI);
        CI->eraseFromParent();

        modified = true;
      } else if (name.equals("__VERIFIER_assert")) {
        CI->eraseFromParent();
        modified = true;
      }
    }
  }
  return modified;
}

} // namespace

static RegisterPass<RemoveErrorCalls> RERC("remove-error-calls",
                                           "Remove calls to __VERIFIER_error");
char RemoveErrorCalls::ID;

// needed for the old slicer
namespace {
  class FindInit : public ModulePass {
    public:
      static char ID;

      FindInit() : ModulePass(ID) {}

      virtual bool runOnModule(Module &M)
      {
        findInitFuns(M);
        // we modified the module
        return true;
      }

    private:
      void findInitFuns(Module &M);
  };
}

void FindInit::findInitFuns(Module &M) {
  SmallVector<Constant *, 1> initFns;
  Type *ETy = TypeBuilder<void *, false>::get(M.getContext());
  Function *_main = M.getFunction("main");
  assert(_main);
  // for the case of NDEBUG
  if (!_main)
    abort();

  initFns.push_back(ConstantExpr::getBitCast(_main, ETy));
  ArrayType *ATy = ArrayType::get(ETy, initFns.size());
  new GlobalVariable(M, ATy, true, GlobalVariable::InternalLinkage,
                     ConstantArray::get(ATy, initFns),
                     "__ai_init_functions");
}

static RegisterPass<FindInit> FINIT("find-init",
                                    "[For the old slicer] Create a global variable and store pointer to main there");
char FindInit::ID;

