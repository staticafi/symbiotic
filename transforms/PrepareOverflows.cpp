#include "llvm/Pass.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/Function.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

#include <set>
#include <vector>
#include <map>

using namespace llvm;

// TODO other operations

namespace {
struct PrepareOverflows : public FunctionPass {
  static char ID;
  PrepareOverflows() : FunctionPass(ID) {}

  void handleExtractValue(ExtractValueInst* EVI) {
      Instruction* I = dyn_cast<Instruction>(EVI->getAggregateOperand());
      if (!I)
          return;

      auto search = binOpsMap.find(I);
      if (search != binOpsMap.end()) {
          if (*(EVI->indices().begin()) == 0) {
              BinaryOperator* binOp = BinaryOperator::CreateNSW(search->second,
                                        I->getOperand(0), I->getOperand(1));
              replaceMap.emplace(EVI, binOp);
          } else if (*(EVI->indices().begin()) == 1) {
              Constant* CI = ConstantInt::getFalse(Type::getInt1Ty(EVI->getContext()));
              replaceMap.emplace(EVI, CI);
          }
      }
  }

  void handleBinOp(Instruction::BinaryOps type, Instruction* I) {
      BinaryOperator::CreateNSW(type, I->getOperand(0), I->getOperand(1));
      binOpsMap.emplace(I, type);
  }

  void handleCall(CallInst* CI) {
      if (!CI->getCalledFunction() || !CI->getCalledFunction()->hasName())
          return;

      auto search = relevantFunctions.find(CI->getCalledFunction()->getName().str());
      if(search != relevantFunctions.end()) {
          deleteInsts.insert(CI);
      }
  }

  void handleSBinOpIntrinsic(IntrinsicInst* II, Instruction::BinaryOps type) {
      deleteInsts.insert(II);
      binOpsMap.emplace(II, type);
  }

  void handleIntrinsic(IntrinsicInst* II) {
      switch (II->getIntrinsicID()) {
          case Intrinsic::sadd_with_overflow:
            handleSBinOpIntrinsic(II, Instruction::BinaryOps::Add);
            break;
          case Intrinsic::ssub_with_overflow:
            handleSBinOpIntrinsic(II, Instruction::BinaryOps::Sub);
            break;
          case Intrinsic::smul_with_overflow:
            handleSBinOpIntrinsic(II, Instruction::BinaryOps::Mul);
            break;
          default:
            break;
      }
  }

  bool runOnFunction(Function &F) override {
      for (auto& BB : F) {
         for (auto& I : BB) {
              if (auto* II = dyn_cast<IntrinsicInst>(&I)) {
                  handleIntrinsic(II);
              } else if (auto* CI = dyn_cast<CallInst>(&I)) {
                  handleCall(CI);
              } else if (auto* EVI = dyn_cast<ExtractValueInst>(&I)) {
                  handleExtractValue(EVI);
              }
          }
      }

      for (const auto& p : replaceMap) {
         if (!p.first || !p.second)
             continue;

         Instruction* I = dyn_cast<Instruction>(p.second);
         if (I)
            ReplaceInstWithInst(p.first, I);
         else {
            BasicBlock::iterator BI(p.first);
            ReplaceInstWithValue(p.first->getParent()->getInstList(), BI, p.second);
         }
      }

      // delete instructions that should be removed
      for (auto i = deleteInsts.rbegin(); i != deleteInsts.rend(); ++i ) {
          (*i)->eraseFromParent();
      }

      deleteInsts.clear();
      binOpsMap.clear();
      replaceMap.clear();
      return false;
  }

 private:
   std::set<Instruction*> deleteInsts;
   std::map<Instruction*, Instruction::BinaryOps> binOpsMap;
   std::map<Instruction*, Value*> replaceMap;
   std::set<std::string> relevantFunctions {
          "__ubsan_handle_add_overflow",
          "__ubsan_handle_sub_overflow",
          "__ubsan_handle_mul_overflow",
          "__ubsan_handle_divrem_overflow",
          "__ubsan_handle_negate_overflow"
   };
};
} // end of anonymous namespace

char PrepareOverflows::ID = 0;
static RegisterPass<PrepareOverflows> PrepOverflows("prepare-overflows", "Prepare for Overflows Instrumentation Pass");
