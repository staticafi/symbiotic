//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.


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
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

using namespace llvm;

namespace {
  class ClassifyInstr : public FunctionPass {
      bool stack_array{false};
      bool stack_var_array{false};
      bool has_malloc{false}, has_calloc{false},
           has_realloc{false}, has_big_malloc{false},
           has_var_malloc{false};
      bool bit_shift{false}, bit_logic{false};

      void classifyInstruction(Instruction& I) {
        if (auto AI = dyn_cast<AllocaInst>(&I)) {
          if (AI->isArrayAllocation()) {
              stack_array = true;
              stack_var_array = true;
          }
          if (AI->getAllocatedType()->isArrayTy()) {
              stack_array = true;
          }
        } else if (auto CI = dyn_cast<CallInst>(&I)) {
#if LLVM_VERSION_MAJOR >= 8
            auto CV = CI->getCalledOperand()->stripPointerCasts();
#else
            auto CV = CI->getCalledValue()->stripPointerCasts();
#endif
            if (CV) {
                const auto& name = cast<Function>(CV)->getName();
                if (name.equals("malloc")) {
                    has_malloc = true;
                    if (auto C = dyn_cast<ConstantInt>(CI->getOperand(0))) {
                        if (C->getZExtValue() > 8)
                            has_big_malloc = true;
                    } else
                        has_var_malloc = true;
                } else if (name.equals("calloc"))
                    has_calloc = true;
                else if (name.equals("realloc"))
                    has_realloc = true;
                else if (name.equals("alloca"))
                    stack_var_array = true;
            }
        } else {
          switch (I.getOpcode()) {
            case Instruction::And:
            case Instruction::Or:
            case Instruction::Xor:
              bit_logic = true;
              break;
            case Instruction::Shl:
            case Instruction::AShr:
            case Instruction::LShr:
              bit_shift = true;
          }
        }

      }

    public:
      static char ID;

      ClassifyInstr() : FunctionPass(ID) {}

      bool runOnFunction(Function &F) override {
        for (auto& B : F) {
          for (auto& I : B) {
            classifyInstruction(I);
          }
        }
        return false;
      }

      bool doFinalization(Module&) override {
        if (stack_array)
            llvm::errs() << "array on stack\n";
        if (stack_var_array)
            llvm::errs() << "alloca or variable-length array\n";
        if (has_malloc) {
          llvm::errs() << "calls malloc\n";
          if (has_big_malloc)
            llvm::errs() << "  > 8b malloc\n";
          if (has_var_malloc)
            llvm::errs() << "  var-sized malloc\n";
        }
        if (has_calloc)
            llvm::errs() << "calls calloc\n";
        if (has_realloc)
            llvm::errs() << "calls reelloc\n";
        if (bit_logic)
            llvm::errs() << "bit-wise operations\n";
        if (bit_shift)
            llvm::errs() << "bit-shift operations\n";
        return false;
      }
  };
}

static RegisterPass<ClassifyInstr> CI("classify-instructions",
                                      "Print statistics from module");
char ClassifyInstr::ID;

