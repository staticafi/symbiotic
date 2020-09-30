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
#if LLVM_VERSION_MAJOR >= 4 || (LLVM_VERSION_MAJOR == 3 && LLVM_VERSION_MINOR >= 5)
  #include "llvm/IR/InstIterator.h"
#else
  #include "llvm/Support/InstIterator.h"
#endif
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <llvm/IR/DebugInfoMetadata.h>

using namespace llvm;

bool CloneMetadata(const llvm::Instruction *, llvm::Instruction *);

class InitializeUninitialized : public ModulePass {
    Function *_vms = nullptr; // verifier_make_nondet function
    Type *_size_t_Ty = nullptr; // type of size_t
    unsigned calls_count = 0;

    std::unique_ptr<DataLayout> DL;

    Function *get_verifier_make_nondet(Module *);
    Type *get_size_t(Module *);
  public:
    static char ID;

    InitializeUninitialized() : ModulePass(ID) {}
    bool runOnFunction(Function &F);

    bool runOnModule(Module& M) override {
      DL = std::unique_ptr<DataLayout>(new DataLayout(M.getDataLayout()));
      bool modified = false;

      for (Function& F : M)
        modified |= runOnFunction(F);

      return modified;
    }
};


static RegisterPass<InitializeUninitialized> INIUNINI("initialize-uninitialized",
                                                      "initialize all uninitialized variables to non-deterministic value");
char InitializeUninitialized::ID;

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

Function *InitializeUninitialized::get_verifier_make_nondet(llvm::Module *M)
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

GlobalVariable *getNameGlobal(Module *M, const std::string& name)
{
  LLVMContext& Ctx = M->getContext();
  Constant *name_init = ConstantDataArray::getString(Ctx, name);
  GlobalVariable *G = new GlobalVariable(*M, name_init->getType(), true,
                                          GlobalValue::PrivateLinkage,
                                          name_init);
  return G;
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
        GlobalVariable *name = getNameGlobal(M, F.getName().str() + ":uninitialized:0");
        Function *C = get_verifier_make_nondet(M);
        // if this is an array allocation, just call verifier_make_nondet on it,
        // since storing whole symbolic array into it would have soo huge overhead
        if (Ty->isArrayTy()) {
            CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(Ctx));
            args.push_back(CastI);
            args.push_back(ConstantInt::get(get_size_t(M), DL->getTypeAllocSize(Ty)));
            args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));
            args.push_back(ConstantInt::get(Type::getInt32Ty(Ctx), ++calls_count));

            CI = CallInst::Create(C, args);
            CastI->insertAfter(AI);
            CI->insertAfter(CastI);

            // we must add these metadata due to the inliner pass, that
            // corrupts the code when metada are missing
            CloneMetadata(AI, CastI);
	        CloneMetadata(AI, CI);
        } else if (AI->isArrayAllocation()) {
            CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(Ctx));
            MulI = BinaryOperator::CreateMul(AI->getArraySize(),
                                             ConstantInt::get(get_size_t(M),
                                                              DL->getTypeAllocSize(Ty)),
                                             "val_size");
            args.push_back(CastI);
            args.push_back(MulI);
            args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));
            args.push_back(ConstantInt::get(Type::getInt32Ty(Ctx), ++calls_count));
            CI = CallInst::Create(C, args);

            CastI->insertAfter(AI);
            MulI->insertAfter(CastI);
            CI->insertAfter(MulI);

            CloneMetadata(AI, CastI);
            CloneMetadata(AI, MulI);
	        CloneMetadata(AI, CI);
        } else {
            // when this is not an array allocation,
            // store the symbolic value into the allocated memory using normal StoreInst.
            // That will allow slice away more unneeded allocations
            auto AIS = new AllocaInst(
                AI->getAllocatedType(),
#if (LLVM_VERSION_MAJOR >= 5)
                AI->getType()->getAddressSpace(),
#endif
                nullptr,
#if LLVM_VERSION_MAJOR >= 11
                AI->getAlign(),
#endif
                "",
                static_cast<Instruction*>(nullptr));
            AIS->insertAfter(AI);

            // we created a new allocation, so now we will make it nondeterministic
            // and store its value into the original allocation
            CastI = CastInst::CreatePointerCast(AIS, Type::getInt8PtrTy(Ctx));
            args.push_back(CastI);
            args.push_back(ConstantInt::get(get_size_t(M), DL->getTypeAllocSize(Ty)));
            args.push_back(ConstantExpr::getPointerCast(name, Type::getInt8PtrTy(Ctx)));
            args.push_back(ConstantInt::get(Type::getInt32Ty(Ctx), ++calls_count));

            CI = CallInst::Create(C, args);
            CastI->insertAfter(AIS);
            CI->insertAfter(CastI);

            LI = new LoadInst(
                AIS->getType()->getPointerElementType(),
                AIS,
                "",
#if LLVM_VERSION_MAJOR >= 11
                false,
                AIS->getAlign(),
#endif
                static_cast<Instruction*>(nullptr));
            SI = new StoreInst(
                LI,
                AI,
                false,
#if LLVM_VERSION_MAJOR >= 11
                LI->getAlign(),
#endif
                static_cast<Instruction*>(nullptr));
            LI->insertAfter(CI);
            SI->insertAfter(LI);

	        CloneMetadata(AI, AIS);
	        CloneMetadata(AI, CI);
	        CloneMetadata(AI, CastI);
	        CloneMetadata(AI, LI);
            CloneMetadata(AI, SI);
        }

        modified = true;
      }
    }
  }

  return modified;
}

