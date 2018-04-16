---
layout: default
navigation_weight: 1
---

## What is Symbiotic?
Symbiotic is a tool for analysis of computer programs. It can check all common safety properties like assertion violations, invalid pointer dereference, double free, memory leaks, etc. Symbiotic uses three well-know techniques: instrumentation, program slicing, and symbolic execution [2]. We use LLVM (<https://llvm.org>) as program representation. Symbiotic is highly modular and not all of its components can be found in this repository. Nevertheless, this repository contains a build script that automatically downloads and builds all required components. Also tarballs with Symbiotic distribution are present in this repository.


## SV-COMP 2018
Symbiotic won the gold medal in MemSafety category, Bronze medal in the FalsificationOverall meta category and took 4th place in the Overall category of SV-COMP 2018. Complete results can be found [here](http://sv-comp.sosy-lab.org/2018/results/results-verified/).

## SV-COMP 2017
We participated in SV-COMP 2017 and we won the bronze medal in MemSafety category! Complete results can be found [here](http://sv-comp.sosy-lab.org/2017/results/results-verified/).

## SV-COMP 2016
We participated in SV-COMP 2016 with this particular release: <https://github.com/staticafi/symbiotic/releases/tag/3.0.1> and we won the bronze medal in Arrays category! Complete results can be found [here](http://sv-comp.sosy-lab.org/2016/results/results-verified/).

### Symbiotic Components

Components of Symbiotic can be found at <https://github.com/staticafi> with the only exception of the slicer, that can be found at <https://github.com/mchalupa/dg> (it will be moved to _staticafi_ in the future though). All parts of Symbiotic are open-source projects and are licensed under various open-source licenses (mainly MIT license, Apache-2.0, University of Illinois Open Source license)

## Contact

For more information send an e-mail to <statica@fi.muni.cz>. We'll be happy to answer your questions :)

------------------------------------------------
[1] Slabý, Jiří and Strejček, Jan and Trtík, Marek. _Checking Properties Described by State Machines: On Synergy of Instrumentation, Slicing, and Symbolic Execution_. <http://is.muni.cz/repo/984069/sse.pdf>

[2] <http://www.fi.muni.cz/~xstrejc/publications/tacas2016symbiotic_preprint.pdf>

[Symbiotic presentation, TACAS 2016](symbiotic_tacas2016.pdf)
