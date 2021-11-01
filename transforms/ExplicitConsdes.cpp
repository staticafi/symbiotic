#include <llvm/IR/Constants.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/InstIterator.h>
#include <llvm/Support/Casting.h>

#include <algorithm>
#include <string>
#include <unordered_map>
#include <vector>

#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Module.h"
#include "llvm/Pass.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"

using namespace llvm;

namespace {

class ExplicitConsdes : public ModulePass {
   private:
    struct FunctionEntry {
        uint32_t priority;
        Function *function;
        Value *param;
    };

    static bool priorityAsc(const FunctionEntry &a, const FunctionEntry &b) {
        return a.priority < b.priority;
    }

    static bool priorityDesc(const FunctionEntry &a, const FunctionEntry &b) {
        return a.priority > b.priority;
    }

    void fillFromInitializer(std::vector<FunctionEntry> &target,
                             Constant *init) {
        auto *ty = init->getType();
        if (!ty->isArrayTy()) {
            errs() << "explicit-consdes: unexpected type of global var "
                      "initializer\n";
            return;
        }

        auto *inner = ty->getArrayElementType();
        if (inner->getStructNumElements() != 3 ||
            !inner->getStructElementType(0)->isIntegerTy() ||
            !inner->getStructElementType(1)
                 ->getPointerElementType()
                 ->isFunctionTy() ||
            !inner->getStructElementType(2)->isPointerTy()) {
            errs() << "explicit-consdes: unexpected type of element in global "
                      "var initializer\n";
            return;
        }

        for (unsigned i = 0; i < init->getType()->getArrayNumElements(); ++i) {
            // type { i32, void ()*, i8* }
            auto *elem = init->getAggregateElement(i);

            FunctionEntry entry{};
            entry.priority =
                dyn_cast<ConstantInt>(elem->getAggregateElement(0u))
                    ->getZExtValue();
            entry.function = dyn_cast<Function>(elem->getAggregateElement(1));
            entry.param = elem->getAggregateElement(2);
            target.push_back(std::move(entry));
        }
    }

    void markUnused(GlobalVariable *gv) {
        if (!gv)
            return;

        gv->setName(gv->getName() + "_unused");
    }

    void insertCalls(std::vector<FunctionEntry> &entries, Instruction *before) {
        Instruction *after = nullptr;

        for (auto &entry : entries) {
            auto *call = CallInst::Create(entry.function, "");

            call->setDebugLoc(before->getDebugLoc());

            if (after) {
                call->insertAfter(after);
            } else {
                call->insertBefore(before);
            }
            after = call;
        }
    }

    bool isExit(const Function *f) {
        const Type *ty = f->getType();
        if (ty->isPointerTy())
            ty = ty->getPointerElementType();

        return f->hasName() && f->getName() == "exit" &&
                    ty->getFunctionNumParams() == 1 &&
                    ty->getFunctionParamType(0)->isIntegerTy();
    }

    bool isMarkExit(const Function *f) {
        const Type *ty = f->getType();
        if (ty->isPointerTy())
            ty = ty->getPointerElementType();
        return f->hasName() && f->getName() == "__INSTR_mark_exit" &&
                    ty->getFunctionNumParams() == 0;
    }

    void warnIfExitIsUsed(const Instruction& inst) {
        // inst -> [operands] -> [only function pointers] -> [only exit] -> is_empty
        for (const auto& op : inst.operands()) {
            const auto *val = op.get();
            if (!val)
                continue;

            const auto *ty = val->getType();

            if (!ty->isPointerTy())
                continue;

            if (!ty->getPointerElementType()->isFunctionTy())
                continue;

            const auto *f = dyn_cast<Function>(val);
            if (!f || !isExit(f))
                continue;

            errs() << "explicit-consdes: warning: indirect call of exit is possible in the program\n";
        }
    }

   public:
    static char ID;

    ExplicitConsdes() : ModulePass(ID) {}

    bool runOnModule(Module &mod) override {
        using std::sort;
        using std::tuple;
        using std::vector;

        vector<FunctionEntry> ctors, dtors;

        GlobalVariable *dtorsVar = mod.getNamedGlobal("llvm.global_dtors");
        GlobalVariable *ctorsVar = mod.getNamedGlobal("llvm.global_ctors");

        if (!ctorsVar && !dtorsVar)
            return false;

        if (dtorsVar) {
            fillFromInitializer(dtors, dtorsVar->getInitializer());
        }

        if (ctorsVar) {
            fillFromInitializer(ctors, ctorsVar->getInitializer());
        }

        // sort them to call order
        sort(ctors.begin(), ctors.end(), priorityAsc);
        sort(dtors.begin(), dtors.end(), priorityDesc);

        // call constructors at the beginning of main
        auto *main = mod.getFunction("main");
        auto *ctorsBefore =
            main->getEntryBlock().getFirstNonPHIOrDbgOrLifetime();
        insertCalls(ctors, ctorsBefore);

        vector<Instruction *> dtorsBefore;

        // search for returns in main
        for (auto &block : *main) {
            if (isa<ReturnInst>(block.getTerminator())) {
                dtorsBefore.push_back(block.getTerminator());
            }
        }

        // if program has __INSTR_mark_exit, we can't insert instruction between it and exit
        bool hasMarkExit = (mod.getFunction("__INSTR_mark_exit") != nullptr);

        // and finally search for calls to exit in whole program
        for (auto &func : mod.functions()) {
            for (auto &inst : instructions(func)) {
                auto *call = dyn_cast<CallInst>(&inst);
                if (!call) {
                    warnIfExitIsUsed(inst);
                    continue;
                }

                Function *called = call->getCalledFunction();
                if (!called) // indirect call
                    continue;

                if (!isExit(called))
                    continue;

                if (!hasMarkExit) {
                    dtorsBefore.push_back(call);
                } else {
                    // look for __INSTR_mark_exit before this call
#if LLVM_VERSION_MAJOR > 7
                    auto *prev = inst.getPrevNonDebugInstruction();
#else
                    auto *prev = inst.getPrevNode();
#endif
                    auto *markCall = prev ? dyn_cast<CallInst>(prev) : nullptr;
                    if (!markCall)
                        continue;

                    Function *markCalled = markCall->getCalledFunction();
                    if (!markCalled) // indirect call
                        continue;

                    if (!isMarkExit(markCalled))
                        continue;

                    dtorsBefore.push_back(markCall);
                }
            }
        }

        for (auto *before : dtorsBefore) {
            insertCalls(dtors, before);
        }

        markUnused(ctorsVar);
        markUnused(dtorsVar);

        return true;
    }
};

char ExplicitConsdes::ID = 0;
static RegisterPass<ExplicitConsdes> X(
    "explicit-consdes",
    "Insert explicit calls of module constructors and destructors",
    false /* Only looks at CFG */, false /* Analysis Pass */);

/*
static RegisterStandardPasses Y(PassManagerBuilder::EP_EarlyAsPossible,
                                [](const PassManagerBuilder &Builder,
                                   legacy::PassManagerBase &PM) {
                                    PM.add(new ExplicitConsdes());
                                });
*/
}  // namespace

