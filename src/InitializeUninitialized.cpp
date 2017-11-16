//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <vector>
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
#include "llvm/IR/TypeBuilder.h"
#if LLVM_VERSION_MAJOR >= 4 || (LLVM_VERSION_MAJOR == 3 && LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <llvm/IR/DebugInfoMetadata.h>

using namespace llvm;

static void CallAddMetadata(CallInst *CI, Instruction *I)
{
  // FIXME: this is just a quick hack, it just makes inliner work,
  // but it gives some spurious lines in witnesses
  if (const DISubprogram *DS = I->getParent()->getParent()->getSubprogram()) {
    // no metadata? then it is going to be the instrumentation
    // of alloca or such at the beggining of function,
    // so just add debug loc of the beginning of the function
    CI->setDebugLoc(DebugLoc::get(DS->getLine(), 0, DS));
  }
}

class InitializeUninitialized : public ModulePass {
    Function *_vms = nullptr; // verifier_make_symbolic function
    Type *_size_t_Ty = nullptr; // type of size_t

    std::unordered_map<Type *, GlobalVariable *> added_globals;
    std::unique_ptr<DataLayout> DL;

    // add global of given type and initialize it in may as nondeterministic
    GlobalVariable *getGlobalNondet(Type *, Module *);
    Function *get_verifier_make_symbolic(Module *);
    Type *get_size_t(Module *);
    bool initializeExternalGlobals(Module&);
  public:
    static char ID;

    InitializeUninitialized() : ModulePass(ID) {}
    bool runOnFunction(Function &F);

    bool runOnModule(Module& M) override {
      DL = std::unique_ptr<DataLayout>(new DataLayout(M.getDataLayout()));
      bool modified = initializeExternalGlobals(M);

      for (Function& F : M)
        modified |= runOnFunction(F);

      return modified;
    }
};


static RegisterPass<InitializeUninitialized> INIUNINI("initialize-uninitialized",
                                                      "initialize all uninitialized variables to non-deterministic value");
char InitializeUninitialized::ID;

bool InitializeUninitialized::initializeExternalGlobals(Module& M) {
  bool modified = false;
  LLVMContext& Ctx = M.getContext();

  for (Module::global_iterator I = M.global_begin(),
                               E = M.global_end(); I != E; ++I) {
    GlobalVariable *GV = &*I;
    if (GV->hasInitializer())
      continue;
    // DONT set the global to be initialized to 0 (null)
    //GV->setInitializer(Constant::getNullValue(GV->getType()->getElementType()));
    GV->setExternallyInitialized(false);
    errs() << "Making global variable '" << GV->getName() << "' non-extern\n";

    // and now make the global symbolic at the beginning of main

    // insert initialization of the new global variable
    // at the beginning of main
    Function *vms = get_verifier_make_symbolic(&M);
    CastInst *CastI = CastInst::CreatePointerCast(GV, Type::getInt8PtrTy(Ctx));
    // GV is a pointer to some memory, we want the size of the memory
    Type *Ty = GV->getType()->getContainedType(0);
    if (!Ty->isSized()) {
      GV->dump();
      llvm::errs() << "WARNING: failed making global variable symbolic (type is unsized)\n";
      continue;
    }

    std::vector<Value *> args;
    args.push_back(CastI);
    args.push_back(ConstantInt::get(get_size_t(&M), DL->getTypeAllocSize(Ty)));
    Constant *name = ConstantDataArray::getString(Ctx, "extern_nondet");
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
    CallAddMetadata(CI, &Inst);

    modified = true;
  }

  return modified;
}

Function *InitializeUninitialized::get_verifier_make_symbolic(llvm::Module *M)
{
  if (_vms)
    return _vms;

  LLVMContext& Ctx = M->getContext();
  //void verifier_make_symbolic(void *addr, size_t nbytes, const char *name);
  Constant *C = M->getOrInsertFunction("__VERIFIER_make_symbolic",
                                       Type::getVoidTy(Ctx),
                                       Type::getInt8PtrTy(Ctx), // addr
                                       get_size_t(M),   // nbytes
                                       Type::getInt8PtrTy(Ctx), // name
                                       nullptr);
  _vms = cast<Function>(C);
  return _vms;
}

Type *InitializeUninitialized::get_size_t(llvm::Module *M)
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

// add global of given type and initialize it in may as nondeterministic
GlobalVariable *InitializeUninitialized::getGlobalNondet(llvm::Type *Ty, llvm::Module *M)
{
  auto it = added_globals.find(Ty);
  if (it != added_globals.end())
    return it->second;

  LLVMContext& Ctx = M->getContext();
  GlobalVariable *G = new GlobalVariable(*M, Ty, false /* constant */,
                                         GlobalValue::PrivateLinkage,
                                         /* initializer */
                                         Constant::getNullValue(Ty),
                                         "nondet_gl");

  added_globals.emplace(Ty, G);

  // insert initialization of the new global variable
  // at the beginning of main
  Function *vms = get_verifier_make_symbolic(M);
  CastInst *CastI = CastInst::CreatePointerCast(G, Type::getInt8PtrTy(Ctx));

  std::vector<Value *> args;
  args.push_back(CastI);
  args.push_back(ConstantInt::get(get_size_t(M), DL->getTypeAllocSize(Ty)));
  Constant *name = ConstantDataArray::getString(Ctx, "nondet");
  GlobalVariable *nameG = new GlobalVariable(*M, name->getType(), true /*constant */,
                                             GlobalVariable::PrivateLinkage, name);
  args.push_back(ConstantExpr::getPointerCast(nameG, Type::getInt8PtrTy(Ctx)));
  CallInst *CI = CallInst::Create(vms, args);

  Function *main = M->getFunction("main");
  assert(main && "Do not have main");
  BasicBlock& block = main->getBasicBlockList().front();
  // there must be some instruction, otherwise we would not be calling
  // this function
  Instruction& I = *(block.begin());
  CastI->insertBefore(&I);
  CI->insertBefore(&I);

  // add metadata due to the inliner pass
  CallAddMetadata(CI, &I);
  //CloneMetadata(&I, CastI);

  return G;
}

// no hard analysis, just check wether the alloca is initialized
// in the same block. (we could do an O(n) analysis that would
// do DFS and if the alloca would be initialized on every path
// before reaching some backedge, then it must be initialized),
// for all allocas the running time would be O(n^2) and it could
// probably be decreased (without pointers)
static bool mayBeUnititialized(const llvm::AllocaInst *AI)
{
	Type *AITy = AI->getAllocatedType();
	if(!AITy->isSized())
		return true;

    const BasicBlock *block = AI->getParent();
    auto I = block->begin();
    auto E = block->end();
    // shift to AI
    while (I != E && (&*I) != AI)
        ++I;

    if (I == E)
        return true;

    // iterate over instructions after AI in this block
    for (++I /* shift after AI */; I != E; ++I) {
        if (const LoadInst *LI = dyn_cast<LoadInst>(&*I)) {
            if (LI->getPointerOperand() == AI)
                return true;
        } else if (const StoreInst *SI = dyn_cast<StoreInst>(&*I)) {
            // we store into AI and we store the same type
            // (that is, we overwrite the whole memory?)
            if (SI->getPointerOperand() == AI &&
                SI->getValueOperand()->getType() == AITy)
                return false;
        }
    }

    return true;
}

bool InitializeUninitialized::runOnFunction(Function &F)
{
  // do not run the initializer on __VERIFIER and __INSTR functions
  const auto& fname = F.getName();
  if (fname.startswith("__VERIFIER_") || fname.startswith("__INSTR_"))
    return false;

  bool modified = false;
  Module *M = F.getParent();
  LLVMContext& Ctx = M->getContext();
  Constant *name_init = ConstantDataArray::getString(Ctx, "nondet");
  GlobalVariable *name = new GlobalVariable(*M, name_init->getType(), true,
                                            GlobalValue::PrivateLinkage,
                                            name_init);

  Function *C = get_verifier_make_symbolic(M);

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E;) {
    Instruction *ins = &*I;
    ++I;

    if (AllocaInst *AI = dyn_cast<AllocaInst>(ins)) {
      if (!mayBeUnititialized(AI))
        continue;

      Type *Ty = AI->getAllocatedType();
      CallInst *CI = nullptr;
      CastInst *CastI = nullptr;
      StoreInst *SI = nullptr;
      LoadInst *LI = nullptr;
      BinaryOperator *MulI = nullptr;

      std::vector<Value *> args;

      // create new allocainst, declare it symbolic and store it
      // to the original alloca. This way slicer will slice this
      // initialization away if program initialize it manually later
      if (Ty->isSized()) {
        // if this is an array allocation, just call verifier_make_symbolic on it,
        // since storing whole symbolic array into it would have soo huge overhead
        if (Ty->isArrayTy()) {
            CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(Ctx));
            args.push_back(CastI);
            args.push_back(ConstantInt::get(get_size_t(M), DL->getTypeAllocSize(Ty)));
            args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));

            CI = CallInst::Create(C, args);
            CastI->insertAfter(AI);
            CI->insertAfter(CastI);

            // we must add these metadata due to the inliner pass, that
            // corrupts the code when metada are missing
            //CloneMetadata(AI, CastI);
	        CallAddMetadata(CI, AI);
        } else if (AI->isArrayAllocation()) {
            CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(Ctx));
            MulI = BinaryOperator::CreateMul(AI->getArraySize(),
                                             ConstantInt::get(get_size_t(M),
                                                              DL->getTypeAllocSize(Ty)),
                                             "val_size");
            args.push_back(CastI);
            args.push_back(MulI);
            args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));
            CI = CallInst::Create(C, args);
            CastI->insertAfter(AI);
            MulI->insertAfter(CastI);
            CI->insertAfter(MulI);

            //CloneMetadata(AI, CastI);
            //CloneMetadata(AI, MulI);
	        CallAddMetadata(CI, AI);
        } else {
            // when this is not an array allocation,
            // store the symbolic value into the allocated memory using normal StoreInst.
            // That will allow slice away more unneeded allocations
            LI = new LoadInst(getGlobalNondet(Ty, M));
            SI = new StoreInst(LI, AI);

            LI->insertAfter(AI);
            SI->insertAfter(LI);

	        //CloneMetadata(AI, LI);
            //CloneMetadata(AI, LI);
        }

        modified = true;
      }
    }
  }

  return modified;
}

