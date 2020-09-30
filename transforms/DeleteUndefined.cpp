//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <vector>
#include <set>
#include <unordered_map>

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
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <llvm/IR/DebugInfoMetadata.h>

#if LLVM_VERSION_MAJOR >= 4
#include <llvm/Support/Error.h>
#endif

using namespace llvm;

bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);

class DeleteUndefined : public ModulePass {
  Function *_vms = nullptr; // verifier_make_symbolic function
  Type *_size_t_Ty = nullptr; // type of size_t
  bool _nosym; // do not use symbolic values when replacing

  // add global of given type and initialize it in may as nondeterministic
  Function *get_verifier_make_nondet(llvm::Module *);
  Type *get_size_t(llvm::Module *);

  unsigned int calls_count = 0;

  //void replaceCall(CallInst *CI, Module *M);
  void defineFunction(Module *M, Function *F);
protected:
  DeleteUndefined(char id) : ModulePass(id), _nosym(true) {}

public:
  static char ID;

  DeleteUndefined() : ModulePass(ID), _nosym(false) {}

  virtual bool runOnModule(Module& M) override;
  bool runOnFunction(Function &F);
};

static RegisterPass<DeleteUndefined> DLTU("delete-undefined",
                                          "delete calls to undefined functions, "
                                          "possible return value is made symbolic");
char DeleteUndefined::ID;

class DeleteUndefinedNoSym : public DeleteUndefined {
  public:
    static char ID;

    DeleteUndefinedNoSym() : DeleteUndefined(ID) {}
};

static RegisterPass<DeleteUndefinedNoSym> DLTUNS("delete-undefined-nosym",
                                          "delete calls to undefined functions, "
                                          "possible return value is made 0");
char DeleteUndefinedNoSym::ID;

static const char *leave_calls[] = {
// KLEE
  "klee_make_symbolic",
  "klee_assume",
  "klee_abort",
  "klee_silent_exit",
  "klee_report_error",
  "klee_warning_once",
  "klee_int",
// standard library
  "__assert_fail",
  "abort",
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
  "__errno_location",
  "__ctype_b_loc",
  "rint",
  "rintf",
  "rintl",
  "lrint",
  "lrintf",
  "lrintl",
  "llrint",
  "llrintf",
  "llrintl",
  "nearbyint",
  "nearbyintf",
  "nearbyintl",
  "remainder",
  "remainderf",
  "remainderl",
  "drem",
  "dremf",
  "dreml",
  "trunc",
  "truncf",
  "truncl",
// fp stuff
  "nan",
  "nanf",
  "nanl",
  "fmax",
  "fmaxf",
  "fmaxl",
  "frexp",
  "ldexp",
  "fabsf",
  "fdim",
  "fmin",
  "fminf",
  "fminl",
  "fmaxf",
  "fmaxl",
  "modf",
  "modff",
  "modfl",
  "copysign",
  "copysignf",
  "copysignl",
  "__isnan",
  "__isnanf",
  "__isnanl",
  "__isinf",
  "__isinff",
  "__isinfl",
  "__fpclassify",
  "__fpclassifyf",
  "__fpclassifyl",
  "__signbit",
  "__signbitf",
  "__signbitl",
  "__finite",
  "__finite1",
  "__finitef",
  "fesetround",
  "round",
  "roundf",
  "roundl",
  "fmod",
  "fmodf",
  "fmodl",
// C++
  "_ZdaPv",
  "_ZdlPv",
  "_Znaj",
  "_Znwj",
  "_Znam",
  "_Znwm",
// pthread stuff
  "pthread_mutex_lock",
  "pthread_mutex_unlock",
  "pthread_mutex_init",
  "pthread_create",
  "pthread_exit",
  "pthread_join",
  "pthread_cond_init",
  "pthread_cond_wait",
  "pthread_cond_signal",
  "pthread_cond_broadcast",
// misc
  "kzalloc",
  nullptr
};

static bool array_match(const StringRef &name, const char **array)
{
  for (const char **curr = array; *curr; curr++)
    if (name.equals(*curr))
      return true;
  return false;
}

bool DeleteUndefined::runOnModule(Module& M) {
#if LLVM_VERSION_MAJOR >= 4
    if (llvm::Error err = M.materializeAll()) {
	std::error_code ec = errorToErrorCode(std::move(err));
	llvm::errs() << __PRETTY_FUNCTION__ << ": cannot load module: " <<
		ec.message();
	return false;
    }
#else
    M.materializeAll();
#endif

    // delete/replace the calls in the rest of functions
    bool modified = false;
    for (auto& F : M.getFunctionList()) {
      if (F.isIntrinsic())
        continue;

      modified |= runOnFunction(F);
    }

    return modified;
}

static unsigned getKleeMakeNondetCounter(const Function *F) {
    using namespace llvm;

    unsigned max = 0;
    for (auto I = F->use_begin(), E = F->use_end(); I != E; ++I) {
#if ((LLVM_VERSION_MAJOR == 3) && (LLVM_VERSION_MINOR < 5))
        const Value *use = *I;
#else
        const Value *use = I->getUser();
#endif
        auto CI = dyn_cast<CallInst>(use);
        assert(CI && "The use is not call");

        auto C = dyn_cast<ConstantInt>(CI->getArgOperand(3));
        assert(C && "Invalid operand in klee_make_nondet");

        auto val = C->getZExtValue();
        if (val > max)
            max = val;
    }

    return max;
}

Function *DeleteUndefined::get_verifier_make_nondet(llvm::Module *M)
{
  if (_vms)
    return _vms;

  LLVMContext& Ctx = M->getContext();
  //void verifier_make_symbolic(void *addr, size_t nbytes, const char *name);
  auto C = M->getOrInsertFunction("klee_make_nondet",
                                  Type::getVoidTy(Ctx),
                                  Type::getInt8PtrTy(Ctx), // addr
                                  get_size_t(M),   // nbytes
                                  Type::getInt8PtrTy(Ctx), // name
                                  Type::getInt32Ty(Ctx) // identifier
#if LLVM_VERSION_MAJOR < 5
                                  , nullptr
#endif
                                  );

#if LLVM_VERSION_MAJOR >= 9
  _vms = cast<Function>(C.getCallee());
#else
  _vms = cast<Function>(C);
#endif

  calls_count = getKleeMakeNondetCounter(_vms);

  return _vms;
}

Type *DeleteUndefined::get_size_t(llvm::Module *M)
{
  if (_size_t_Ty)
    return _size_t_Ty;

  std::unique_ptr<DataLayout> DL
    = std::unique_ptr<DataLayout>(new DataLayout(M->getDataLayout()));
  LLVMContext& Ctx = M->getContext();

  if (DL->getPointerSizeInBits() > 32)
    _size_t_Ty = Type::getInt64Ty(Ctx);
  else
    _size_t_Ty = Type::getInt32Ty(Ctx);

  return _size_t_Ty;
}

void DeleteUndefined::defineFunction(Module *M, Function *F)
{
  assert(F->size() == 0);
  assert(!F->getReturnType()->isVoidTy());

  LLVMContext& Ctx = M->getContext();
  BasicBlock *block = BasicBlock::Create(Ctx, "entry", F);
  if (_nosym) {
    // replace the return value with 0, since we don't want
    // to use the symbolic value
    ReturnInst::Create(Ctx, Constant::getNullValue(F->getReturnType()), block);
  } else {
    Type *Ty = F->getReturnType();
    AllocaInst *AI = new AllocaInst(
        Ty,
#if (LLVM_VERSION_MAJOR >= 5)
        0,
#endif
        nullptr,
        "",
        block);

    // insert initialization of the new global variable
    // at the beginning of main
    Function *vms = get_verifier_make_nondet(M);
    CastInst *CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(Ctx));
    CastI->insertAfter(AI);

    std::vector<Value *> args;
    args.push_back(CastI);
    args.push_back(ConstantInt::get(get_size_t(M),
                   M->getDataLayout().getTypeAllocSize(Ty)));
    std::string namestr = F->getName().str();
    namestr += ":undeffun:0";
    Constant *name = ConstantDataArray::getString(Ctx, namestr);
    GlobalVariable *nameG = new GlobalVariable(*M, name->getType(), true /*constant */,
                                               GlobalVariable::PrivateLinkage, name);
    args.push_back(ConstantExpr::getPointerCast(nameG, Type::getInt8PtrTy(Ctx)));
    args.push_back(ConstantInt::get(Type::getInt32Ty(Ctx), ++calls_count));

    CallInst *CI = CallInst::Create(vms, args);
    CI->insertAfter(CastI);

    LoadInst *LI = new LoadInst(
        AI->getType()->getPointerElementType(),
        AI,
        "undefret",
        block);
    ReturnInst::Create(Ctx, LI, block);
  }

  F->setLinkage(GlobalValue::LinkageTypes::InternalLinkage);
}

bool DeleteUndefined::runOnFunction(Function &F)
{
  // static set for the calls that we removed, so that
  // we can print those call only once
  static std::set<const llvm::Value *> removed_calls;
  Module *M = F.getParent();

  if (F.getName().startswith("__VERIFIER_"))
    return false;

  if (array_match(F.getName(), leave_calls))
    return false;

  if (F.empty() && !F.getReturnType()->isVoidTy()) {
    errs() << "Defining function " << F.getName() << " as symbolic\n";
    defineFunction(M, &F);
    return true;
  }

  // nothing to do here...
  if (F.empty())
    return false;

  // if the function is defined, just delete the calls to undefined
  // functions that does not return anything (if it does return anything,
  // it was/will be fixed in defineFunction()
  bool modified = false;
  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;
    if (CallInst *CI = dyn_cast<CallInst>(ins)) {
      if (CI->isInlineAsm())
        continue;

#if LLVM_VERSION_MAJOR >= 8
      Value *val = CI->getCalledOperand()->stripPointerCasts();
#else
      Value *val = CI->getCalledValue()->stripPointerCasts();
#endif
      Function *callee = dyn_cast<Function>(val);
      // if this is intrinsic call or a call via a function pointer,
      // let it be
      // XXX: do we handle the function pointers correctly? What if there
      // is only a declaration of a function and it is taken to pointer
      // and then called? We do not define it in this case...
      if (!callee || callee->isIntrinsic())
        continue;

      // here we continue only with undefined function that return nothing,
      // becuase the functions that return something were/will be
      // defined in defineFunction()
      if (!callee->getReturnType()->isVoidTy())
        continue;

      assert(callee->hasName());
      StringRef name = callee->getName();

      // if this is __VERIFIER_* call, keep it
      if (name.startswith("__VERIFIER_"))
        continue;

      if (array_match(name, leave_calls))
        continue;

      if (callee->isDeclaration()) {
        if (removed_calls.insert(callee).second)
            errs() << "Removed calls to '" << name << "' (function is undefined)\n";

        // remove the call
        assert(CI->getType()->isVoidTy());
        CI->eraseFromParent();
        modified = true;
      }
    }
  }
  return modified;
}

