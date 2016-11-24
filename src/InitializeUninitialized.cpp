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
#include "llvm/IR/TypeBuilder.h"
#if (LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

using namespace llvm;

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
  // do not run the initializer on __VERIFIER and __INSTR functions
  const auto& fname = F.getName();
  if (fname.startswith("__VERIFIER_") || fname.startswith("__INSTR_"))
    return false;

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

