//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
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

static cl::opt<std::string> source_name("make-nondet-source",
                                        cl::desc("Specify source filename"),
                                        cl::value_desc("filename"));


class MakeNondet : public ModulePass {
  // every item is (line number, call)
  std::vector<std::pair<unsigned, CallInst *>> calls_to_replace;
  std::vector<std::pair<unsigned, CallInst *>> allocs_to_handle;
  std::set<unsigned> lines_nums;
  std::map<unsigned, std::string> lines;
  Function *_vms = nullptr; // verifier_make_symbolic function
  Type *_size_t_Ty = nullptr; // type of size_t

  void handleCall(Function& F, CallInst *CI, bool ismalloc);
  void mapLines();
  void replaceCalls(Module& M);
  void handleAllocs(Module& M);
  void replaceCall(Module& M, CallInst *CI, unsigned line, const std::string& var);
  void handleAlloc(Module& M, CallInst *CI, unsigned line, const std::string& var);

  // add global of given type and initialize it in may as nondeterministic
  Function *get_verifier_make_nondet(llvm::Module&);
  Type *get_size_t(llvm::Module& );

  unsigned call_identifier = 0;

public:
  static char ID;

  MakeNondet() : ModulePass(ID) {}
  void runOnFunction(Function &F);
  // must be module pass, so that we can iterate over
  // declarations too
  virtual bool runOnModule(Module &M) {
    for (auto& F : M)
      runOnFunction(F);

    mapLines();
    replaceCalls(M);
    handleAllocs(M);

    return !calls_to_replace.empty() || !allocs_to_handle.empty();
  }
};

void MakeNondet::runOnFunction(Function &F) {
  if (F.isDeclaration())
    return;

  for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E; ++I) {
    if (CallInst *CI = dyn_cast<CallInst>(&*I)) {
#if LLVM_VERSION_MAJOR >= 8
      auto fun = dyn_cast<Function>(CI->getCalledOperand()->stripPointerCasts());
#else
      auto fun = dyn_cast<Function>(CI->getCalledValue()->stripPointerCasts());
#endif
      if (!fun)
          continue;
      auto name = fun->getName();
      if (name.equals("malloc") || name.equals("calloc") ||
          name.startswith("__VERIFIER_nondet"))
        handleCall(F, CI, !name.startswith("__VERIFIER"));
    }
  }
}

void MakeNondet::handleCall(Function& F, CallInst *CI, bool ismalloc) {
  const DebugLoc& Loc = CI->getDebugLoc();
  if (Loc) {
    if (ismalloc)
	    allocs_to_handle.emplace_back(Loc.getLine(), CI);
    else
	    calls_to_replace.emplace_back(Loc.getLine(), CI);
    lines_nums.insert(Loc.getLine());
  } else {
    if (ismalloc)
	    allocs_to_handle.emplace_back(0, CI);
    else
	    calls_to_replace.emplace_back(0, CI);
  }
}

void MakeNondet::mapLines() {
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

void MakeNondet::replaceCall(Module& M, CallInst *CI,
                                      unsigned line, const std::string& var) {
  // NOTE: this must be called before using call_identifier
  auto make_nondet = get_verifier_make_nondet(M);
  std::string parent_name = cast<Function>(CI->getParent()->getParent())->getName().str();
  std::string name = parent_name + ":" + var + ":" + std::to_string(line);
  Constant *name_const = ConstantDataArray::getString(M.getContext(), name);
  GlobalVariable *nameG = new GlobalVariable(M, name_const->getType(), true /*constant */,
                                             GlobalVariable::PrivateLinkage, name_const);

  AllocaInst *AI = new AllocaInst(
      CI->getType(),
#if (LLVM_VERSION_MAJOR >= 5)
      0,
#endif
      nullptr,
#if LLVM_VERSION_MAJOR >= 11
      M.getDataLayout().getPrefTypeAlign(CI->getType()),
#endif
      "",
      static_cast<Instruction*>(nullptr));

  CastInst *CastI = CastInst::CreatePointerCast(AI, Type::getInt8PtrTy(M.getContext()));

  std::vector<Value *> args;
  // memory
  args.push_back(CastI);
  // nbytes
  args.push_back(ConstantInt::get(get_size_t(M),
                                  M.getDataLayout().getTypeAllocSize(CI->getType())));
  // name
  args.push_back(ConstantExpr::getPointerCast(nameG,
                                              Type::getInt8PtrTy(M.getContext())));
  // identifier
  args.push_back(ConstantInt::get(Type::getInt32Ty(M.getContext()), ++call_identifier));

  CallInst *new_CI = CallInst::Create(make_nondet, args);
  if (auto Loc = CI->getDebugLoc())
    new_CI->setDebugLoc(Loc);

  LoadInst *LI = new LoadInst(
#if LLVM_VERSION_MAJOR >= 8
      AI->getType()->getPointerElementType(),
#endif
      AI,
      name,
#if LLVM_VERSION_MAJOR >= 11
      false,
      AI->getAlign(),
#endif
      static_cast<Instruction*>(nullptr));

  new_CI->insertBefore(CI);

  CastI->insertBefore(new_CI);
  AI->insertBefore(CastI);
  LI->insertAfter(new_CI);
  CI->replaceAllUsesWith(LI);
  CI->eraseFromParent();
}

void MakeNondet::handleAlloc(Module& M, CallInst *CI,
                                      unsigned line, const std::string& var) {
  auto make_nondet = get_verifier_make_nondet(M);
  std::string parent_name = cast<Function>(CI->getParent()->getParent())->getName().str();
  std::string name = parent_name + ":" + var + ":" + std::to_string(line);
  Constant *name_const = ConstantDataArray::getString(M.getContext(), name);
  GlobalVariable *nameG = new GlobalVariable(M, name_const->getType(), true /*constant */,
                                             GlobalVariable::PrivateLinkage, name_const);

  CastInst *CastI = CastInst::CreatePointerCast(CI, Type::getInt8PtrTy(M.getContext()));
  CastI->insertAfter(CI);

  std::vector<Value *> args;
  // memory
  args.push_back(CastI);
  // nbytes
  if (CI->getCalledFunction()->getName().equals("calloc")) {
    auto Mul = BinaryOperator::Create(Instruction::Mul,
                                      CI->getOperand(0),
                                      CI->getOperand(1));
    auto CastI2 = CastInst::CreateZExtOrBitCast(Mul, get_size_t(M));
    Mul->insertBefore(CastI);
    CastI2->insertAfter(Mul);
    args.push_back(CastI2);
  } else {
    auto CastI2 = CastInst::CreateZExtOrBitCast(CI->getOperand(0), get_size_t(M));
    CastI2->insertBefore(CastI);
    args.push_back(CastI2);
  }

  // name
  args.push_back(ConstantExpr::getPointerCast(nameG,
                                              Type::getInt8PtrTy(M.getContext())));
  // identifier
  args.push_back(ConstantInt::get(Type::getInt32Ty(M.getContext()), ++call_identifier));

  CallInst *new_CI = CallInst::Create(make_nondet, args);
  if (auto Loc = CI->getDebugLoc())
    new_CI->setDebugLoc(Loc);
  new_CI->insertAfter(CastI);
}

static std::string strip(const std::string& str) {
    size_t start = 0, end = str.length() - 1;
    while (start < str.length() && std::isspace(str[start]))
        ++start;
    while (std::isspace(str[end]))
        --end;
    assert(start <= end);
    return str.substr(start, end - start + 1);
}

static std::string lastWord(const std::string& str) {
    size_t end = str.length() - 1;

    // skip the whitespace at the end
    while (std::isspace(str[end]))
        --end;

    while (!std::isspace(str[end])) {
        if (end == 0)
            return str;

        --end;
    }

    return str.substr(end + 1);
}

static inline bool startswith(const std::string& str, const std::string& with) {
    return str.compare(0, with.length(), with) == 0;
}

static std::string getName(const std::string& line) {
  auto pos = line.find("=");
  if (pos == std::string::npos)
      return "--";

  std::string var = lastWord(strip(line.substr(0, pos)));
  std::string expr = strip(line.substr(pos + 1));
  //errs() << " var: " << var << "\n";
  //errs() << " expr: " << expr << "\n";
  if (!var.empty() && !expr.empty()) {
    // this may make problems with casting, line: (int) __VERIFIER_nondet_char()
    // maybe this is not needed?
    if (startswith(expr, "__VERIFIER_nondet_")/* ||
        startswith(expr, "malloc") || startswith(expr, "calloc") ||
        startswith(expr, "realloc") || startswith(expr, "alloca") ||
        startswith(expr, "__builtin_alloca")*/)
		return var;
  }

  return "--";
}

void MakeNondet::replaceCalls(Module& M) {
  for (auto& pr : calls_to_replace) {
    unsigned line_num = pr.first;
	CallInst *CI = pr.second;

    auto it = lines.find(line_num);
    replaceCall(M, CI, line_num,
                it == lines.end() ? "" : getName(it->second));
  }
}

void MakeNondet::handleAllocs(Module& M) {
  for (auto& pr : allocs_to_handle) {
    unsigned line_num = pr.first;
	CallInst *CI = pr.second;

    auto it = lines.find(line_num);
    auto name = getName(it->second);
    handleAlloc(M, CI, line_num, name == "--" ? "%dynalloc" : name);
  }
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

Function *MakeNondet::get_verifier_make_nondet(llvm::Module& M)
{
  if (_vms)
    return _vms;

  LLVMContext& Ctx = M.getContext();
  //void verifier_make_symbolic(void *addr, size_t nbytes, const char *name);
  auto C = M.getOrInsertFunction("klee_make_nondet",
                                 Type::getVoidTy(Ctx),
                                 Type::getInt8PtrTy(Ctx), // addr
                                 // FIXME: get rid of the nbytes
                                 // -- make the object symbolic entirely
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

  call_identifier = getKleeMakeNondetCounter(_vms);

  return _vms;
}

Type *MakeNondet::get_size_t(llvm::Module& M)
{
  if (_size_t_Ty)
    return _size_t_Ty;

  LLVMContext& Ctx = M.getContext();

  if (M.getDataLayout().getPointerSizeInBits() > 32)
    _size_t_Ty = Type::getInt64Ty(Ctx);
  else
    _size_t_Ty = Type::getInt32Ty(Ctx);

  return _size_t_Ty;
}

static RegisterPass<MakeNondet> MND("make-nondet",
                                    "Replace calls to verifier funs with code "
                                    " that registers new symbolic objects "
                                    "with KLEE. Also, make dynamically allocated "
                                    "memory contain nondeterministic values too");
char MakeNondet::ID;

