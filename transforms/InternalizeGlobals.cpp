//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
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
#include <llvm/IR/DebugInfoMetadata.h>

using namespace llvm;

bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);

class InternalizeGlobals : public ModulePass {
    Function *_vms = nullptr; // verifier_make_nondet function
    Type *_size_t_Ty = nullptr; // type of size_t

    std::unique_ptr<DataLayout> DL;

    Function *get_verifier_make_nondet(Module *);
    Type *get_size_t(Module *);
    bool initializeExternalGlobals(Module&);
  public:
    static char ID;

    InternalizeGlobals() : ModulePass(ID) {}

    bool runOnModule(Module& M) override {
      DL = std::unique_ptr<DataLayout>(new DataLayout(M.getDataLayout()));
      return initializeExternalGlobals(M);
    }
};


static RegisterPass<InternalizeGlobals> IG("internalize-globals",
                                           "internalize and make non-deterministic"
                                           "external globals");
char InternalizeGlobals::ID;

bool InternalizeGlobals::initializeExternalGlobals(Module& M) {
  bool modified = false;
  LLVMContext& Ctx = M.getContext();

  for (Module::global_iterator I = M.global_begin(),
                               E = M.global_end(); I != E; ++I) {
    GlobalVariable *GV = &*I;
    if (GV->hasInitializer())
      continue;

    // insert initialization of the new global variable
    // at the beginning of main

    // GV is a pointer to some memory, we want the size of the memory
    Type *Ty = GV->getType()->getContainedType(0);
    if (!Ty->isSized()) {
      llvm::errs() << *GV << "\n";
      llvm::errs() << "ERROR: failed making global variable symbolic "
                      "(type is unsized)\n";
      continue;
    }

    // skip standard objects defined in libc
    if (GV->hasName()) {
      const auto& name = GV->getName();
      if (name.equals("stdin") || name.equals("stderr") ||
          name.equals("stdout")) {
        continue;
      }
    }

    // what memory will be made symbolic
    Value *memory = GV;

    // the global is a pointer, so we will create an object that it can
    // point to and set it to symbolic at the beggining of main
    if (Ty->isPointerTy()) {
        if (!Ty->getContainedType(0)->isSized()) {
            llvm::errs() << *GV << "\n";
            llvm::errs() << "ERROR: failed making global variable symbolic "
                            "(referenced type is unsized)\n";
            continue;
        }

        // maybe we should do that recursively? Until we get a non-pointer?
        Constant *init = Constant::getNullValue(Ty->getContainedType(0));
        GlobalVariable *pointedG
            = new GlobalVariable(M, Ty->getContainedType(0),
                                 false /*constant */,
                                 GlobalVariable::PrivateLinkage,
                                 init);
        GV->setInitializer(pointedG);

        // set memory and its type that should be made symbolic
        memory = pointedG;
        Ty = Ty->getContainedType(0);
    } else {
        // we need to set some initializer, otherwise the global
        // won't be marked as non-external. This initializer will
        // be overwritten at the beginning of main for most of the globals
        if (GV->hasName() && GV->getName().equals("optind")) {
            GV->setInitializer(
                ConstantInt::get(Type::getInt32Ty(M.getContext()), 1)
            );
        } else {
            GV->setInitializer(Constant::getNullValue(GV->getValueType()));
        }
    }

    if (GV->hasName()) {
      const auto& name = GV->getName();
      if (name.equals("optind") || name.equals("optarg")) {
        // keep the optind and optarg variables initialized to 1 and null
        continue;
      }
    }

    Function *vms = get_verifier_make_nondet(&M);
    CastInst *CastI = CastInst::CreatePointerCast(memory, Type::getInt8PtrTy(Ctx));

    std::vector<Value *> args;
    args.push_back(CastI);
    args.push_back(ConstantInt::get(get_size_t(&M), DL->getTypeAllocSize(Ty)));
    std::string nameStr = GV->hasName() ? GV->getName().str() : "extern-global";
    Constant *name
        = ConstantDataArray::getString(Ctx, nameStr);
    GlobalVariable *nameG = new GlobalVariable(M, name->getType(), true /*constant */,
                                               GlobalVariable::PrivateLinkage, name);
    args.push_back(ConstantExpr::getPointerCast(nameG, Type::getInt8PtrTy(Ctx)));
    CallInst *CI = CallInst::Create(vms, args);

    Function *main = M.getFunction("main");
    assert(main && "Do not have main");
    BasicBlock& block = main->getBasicBlockList().front();
    // there must be some instruction, otherwise we would not be calling
    // this function
    Instruction& Inst = *(block.begin());
    CastI->insertBefore(&Inst);
    CI->insertBefore(&Inst);

    // add metadata due to the inliner pass
    CloneMetadata(&Inst, CI);

    modified = true;

    GV->setExternallyInitialized(false);
    // make it writable as we're going to inicialize it in main
    GV->setConstant(false);
    errs() << "Made global variable '" << GV->getName() << "' non-extern\n";
  }

  return modified;
}

Function *InternalizeGlobals::get_verifier_make_nondet(llvm::Module *M)
{
  if (_vms)
    return _vms;

  LLVMContext& Ctx = M->getContext();
  //void verifier_make_symbolic(void *addr, size_t nbytes, const char *name);
  auto C = M->getOrInsertFunction("__VERIFIER_make_nondet",
                                   Type::getVoidTy(Ctx),
                                   Type::getInt8PtrTy(Ctx), // addr
                                   get_size_t(M),   // nbytes
                                   Type::getInt8PtrTy(Ctx) // name
#if LLVM_VERSION_MAJOR < 5
                                   , nullptr
#endif
                                   );
#if LLVM_VERSION_MAJOR >= 9
  _vms = cast<Function>(C.getCallee());
#else
  _vms = cast<Function>(C);
#endif


  return _vms;
}

Type *InternalizeGlobals::get_size_t(llvm::Module *M)
{
  if (_size_t_Ty)
    return _size_t_Ty;

  LLVMContext& Ctx = M->getContext();

  if (DL->getPointerSizeInBits() > 32)
    _size_t_Ty = Type::getInt64Ty(Ctx);
  else
    _size_t_Ty = Type::getInt32Ty(Ctx);

  return _size_t_Ty;
}

