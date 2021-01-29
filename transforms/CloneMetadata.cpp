//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.

#include <cassert>
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Support/raw_ostream.h"
#include <llvm/IR/DebugInfoMetadata.h>

using namespace llvm;

/** Clone metadata from one instruction to another.
 * If i1 does not contain any metadata, then the instruction
 * that is closest to i1 is picked (we prefer the one that is after
 * and if there is none, then use the closest one before).
 *
 * @param i1 the first instruction
 * @param i2 the second instruction without any metadata
 */
bool CloneMetadata(const llvm::Instruction *i1, llvm::Instruction *i2)
{
    if (i1->hasMetadata()) {
        i2->setDebugLoc(i1->getDebugLoc());
        return true;
    }

    const llvm::Instruction *metadataI = nullptr;
    bool after = false;
    for (const llvm::Instruction& I : *i1->getParent()) {
        if (&I == i1) {
            after = true;
            continue;
        }

        if (I.hasMetadata()) {
            // store every "last" instruction with metadata,
            // so that in the case that we won't find anything
            // after i1, we can use metadata that are the closest
            // "before" i1
            metadataI = &I;
            if (after)
                break;
        }
    }

    //assert(metadataI && "Did not find dbg in any instruction of a block");
    if (metadataI) {
        i2->setDebugLoc(metadataI->getDebugLoc());
    } else if (auto pred = i1->getParent()->getUniquePredecessor()) {
        return CloneMetadata(pred->getTerminator(), i2);
    } else {
      DebugLoc DL;
      if (auto SP = i1->getParent()->getParent()->getSubprogram()) {
        DL = DILocation::get(SP->getContext(), SP->getScopeLine(), 0, SP);
      }
      i2->setDebugLoc(DL);
    }

    return i2->hasMetadata();
}

