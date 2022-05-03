//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include <map>
#include <vector>
#include <set>
#include <fstream>
#include <sstream>

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

#include "llvm/Support/CommandLine.h"

using namespace llvm;

static cl::opt<std::string> source_name("rename-verifier-funs-source",
                                        cl::desc("Specify source filename"),
                                        cl::value_desc("filename"));


class RenameVerifierFuns : public ModulePass
{
  // every item is (line number, call)
  std::vector<std::pair<unsigned, CallInst *>> calls_to_replace;
  std::set<unsigned> lines_nums;
  std::map<unsigned, std::string> lines;

  void handleCall(Function& F, CallInst *CI);
  void mapLines();
  void replaceCalls(Module& M);

public:
  static char ID;

  RenameVerifierFuns() : ModulePass(ID) {}
  bool runOnFunction(Function &F);
  // must be module pass, so that we can iterate over
  // declarations too
  virtual bool runOnModule(Module &M) {
    for (auto& F : M)
      runOnFunction(F);

    mapLines();
    replaceCalls(M);
    return !calls_to_replace.empty();
  }
};

bool RenameVerifierFuns::runOnFunction(Function &F) {
  if (!F.isDeclaration())
    return false;

  StringRef name = F.getName();
  if (!name.startswith("__VERIFIER_nondet_"))
    return false;

  bool changed = false;

  //llvm::errs() << "Got __VERIFIER_fun: " << name << "\n";

  for (auto I = F.use_begin(), E = F.use_end(); I != E; ++I) {
#if ((LLVM_VERSION_MAJOR == 3) && (LLVM_VERSION_MINOR < 5))
    Value *use = *I;
#else
    Value *use = I->getUser();
#endif

    if (CallInst *CI = dyn_cast<CallInst>(use)) {
      handleCall(F, CI);
    }
  }

  return changed;
}

void RenameVerifierFuns::handleCall(Function& /*F*/, CallInst *CI) {
  const DebugLoc& Loc = CI->getDebugLoc();
  if (Loc) {
	calls_to_replace.emplace_back(Loc.getLine(), CI);
    lines_nums.insert(Loc.getLine());
  }
}

void RenameVerifierFuns::mapLines() {
  if (lines_nums.empty()) {
    assert(calls_to_replace.empty());
    return;
  }

  std::ifstream file(source_name);

  if (file.is_open()) {
    unsigned n = 1;
    std::string line;

    while (getline(file,line)) {
      if (lines_nums.count(n) > 0)
		lines[n] = std::move(line);
      ++n;
    }

    file.close();
  } else {
	errs() << "Couldn't open file: " << source_name << "\n";
    abort();
  }

  assert(lines.size() == lines_nums.size());
}

static void replaceCall(Module& M, CallInst *CI, unsigned line, const std::string& var) {
  std::string parent_name = cast<Function>(CI->getParent()->getParent())->getName().str();
  std::string name = parent_name + ":" + var + ":" + std::to_string(line);
  Function *called_func = CI->getCalledFunction();
  auto new_func = M.getOrInsertFunction(called_func->getName().str() + "_named",
								        called_func->getAttributes(),
									    called_func->getReturnType(),
                                        Type::getInt8PtrTy(M.getContext())
#if LLVM_VERSION_MAJOR < 5
                                             , nullptr
#endif
                                       );
  assert(new_func);

  std::vector<Value *> args;
  Constant *name_const = ConstantDataArray::getString(M.getContext(), name);
  GlobalVariable *nameG = new GlobalVariable(M, name_const->getType(), true /*constant */,
                                             GlobalVariable::PrivateLinkage, name_const);
  args.push_back(ConstantExpr::getPointerCast(nameG,
                                              Type::getInt8PtrTy(M.getContext())));

  CallInst *new_CI = CallInst::Create(new_func, args);
  SmallVector<std::pair<unsigned, MDNode *>, 8> metadata;
  CI->getAllMetadata(metadata);
  // copy the metadata
  for (auto& md : metadata)
    new_CI->setMetadata(md.first, md.second);
  // copy the attributes (like zeroext etc.)
  new_CI->setAttributes(CI->getAttributes());

  new_CI->insertBefore(CI);
  CI->replaceAllUsesWith(new_CI);
  CI->eraseFromParent();
}

static std::string getName(const std::string& line) {
  std::istringstream iss(line);
  std::string sub, var;
  while (iss >> sub) {
    if (sub == "=") {
	  break;
    }
	var = std::move(sub);
  }

  if (!var.empty() && sub == "=") {
    // check also that after = follows the __VERIFIER_* call
    iss >> sub;
    // this may make problems with casting, line: (int) __VERIFIER_nondet_char()
    // maybe this is not needed?
    if (sub.compare(0, 18, "__VERIFIER_nondet_") == 0)
		return var;
  }

  return "--";
}

void RenameVerifierFuns::replaceCalls(Module& M) {
  for (auto& pr : calls_to_replace) {
    unsigned line_num = pr.first;
	CallInst *CI = pr.second;

    std::string line = lines[line_num];
    assert(!line.empty());

    replaceCall(M, CI, line_num, getName(line));
  }
}


static RegisterPass<RenameVerifierFuns> RVF("rename-verifier-funs",
                                            "Replace calls to verifier funs with calls to our funs");
char RenameVerifierFuns::ID;

