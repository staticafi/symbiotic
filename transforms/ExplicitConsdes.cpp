#include <llvm/IR/Constants.h>
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
        Value *function;
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
            entry.function = elem->getAggregateElement(1);
            entry.param = elem->getAggregateElement(2);
            target.push_back(std::move(entry));
        }
    }

    void insertCalls(std::vector<FunctionEntry> &entries, Instruction *before) {
        Instruction *after = nullptr;

        for (auto &entry : entries) {
            auto *call = CallInst::Create(
                dyn_cast<FunctionType>(
                    entry.function->getType()->getPointerElementType()),
                entry.function, "");
            call->setDebugLoc(DebugLoc::get(0,0, before->getDebugLoc().getScope()));
            if (after) {
                call->insertAfter(after);
            } else {
                call->insertBefore(before);
            }
            after = call;
        }
    }

   public:
    static char ID;

    ExplicitConsdes() : ModulePass(ID) {}

    bool runOnModule(Module &mod) override {
        using std::sort;
        using std::tuple;
        using std::vector;

        bool change = false;

        vector<FunctionEntry> ctors, dtors;

        GlobalVariable *dtorsVar = nullptr;
        GlobalVariable *ctorsVar = nullptr;

        for (auto &glob : mod.globals()) {
            if (glob.hasName() && glob.getName() == "llvm.global_dtors") {
                fillFromInitializer(dtors, glob.getInitializer());
                dtorsVar = &glob;
            }

            if (glob.hasName() && glob.getName() == "llvm.global_ctors" &&
                glob.hasInitializer()) {
                fillFromInitializer(ctors, glob.getInitializer());
                ctorsVar = &glob;
            }
        }

        if (ctors.empty() && dtors.empty()) {
            return false;
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

        // and finally search for calls to exit in whole program
        for (auto &func : mod.functions()) {
            for (auto &block : func) {
                for (auto &inst : block) {
                    if (auto *call = dyn_cast<CallInst>(&inst)) {
                        if (call->isIndirectCall()) continue;
                        Function *called = call->getCalledFunction();
                        if (!called) continue;
                        auto *ty = called->getType()->getPointerElementType();
                        if (called->hasName() && called->getName() == "exit" &&
                            ty->getFunctionNumParams() == 1 &&
                            ty->getFunctionParamType(0)->isIntegerTy()) {
                            dtorsBefore.push_back(call);
                        }
                    }
                }
            }
        }

        for (auto *before : dtorsBefore) {
            insertCalls(dtors, before);
        }

        if (ctorsVar) {
            ctorsVar->eraseFromParent();
        }
        if (dtorsVar) {
            dtorsVar->eraseFromParent();
        }

        return true;
    }
};

char ExplicitConsdes::ID = 0;
static RegisterPass<ExplicitConsdes> X(
    "explicit-consdes",
    "Insert explicit calls of module constructors and destructors",
    false /* Only looks at CFG */, false /* Analysis Pass */);

static RegisterStandardPasses Y(PassManagerBuilder::EP_EarlyAsPossible,
                                [](const PassManagerBuilder &Builder,
                                   legacy::PassManagerBase &PM) {
                                    PM.add(new ExplicitConsdes());
                                });
}  // namespace

