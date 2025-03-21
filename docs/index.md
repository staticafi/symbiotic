## What is Symbiotic?
Symbiotic is a framework for analysis of computer programs written in the programming language C. It can check all common safety properties like assertion violations, invalid pointer dereference, double free, memory leaks, etc. Additionally, it can decide termination property. Symbiotic combines static analysis, compile-time code instrumentation, program slicing, and symbolic execution and it integrates several libraries and tools including [DG](https://github.com/mchalupa/dg), our clone of [Klee](http://klee.github.io/) called [JetKlee](https://github.com/staticafi/JetKlee), [Predator](http://www.fit.vutbr.cz/research/groups/verifit/tools/predator/), [SlowBeast](https://gitlab.fi.muni.cz/xchalup4/slowbeast), [Z3](https://github.com/Z3Prover/z3) and others. The framework uses [LLVM](<https://llvm.org>) as internal program representation. Symbiotic is highly modular and all of its components can be used separately.

### Symbiotic Components

Components of Symbiotic can be found at <https://github.com/staticafi> with the only exception of the slicer, that can be found at <https://github.com/mchalupa/dg> (it will be moved to _staticafi_ in the future though). All parts of Symbiotic are open-source projects and are licensed under various open-source licenses (GPL, MIT license, University of Illinois Open Source license).

## Awards
* Symbiotic 10.1 participating in [SV-COMP 2025](https://sv-comp.sosy-lab.org/2025/results/results-verified/), compiled version available at [Zenodo](https://zenodo.org/records/14230101)
  * 2nd in MemSafety
  * 2nd in FalsificationOverall
  * 3rd in SoftwareSystems
  * **3rd in Overall**
* Symbiotic 10.1 participating in [Test-Comp 2025](https://test-comp.sosy-lab.org/2025/results/results-verified/), compiled version available at [Zenodo](https://zenodo.org/records/14230101)
  * 3rd in Cover-Error 
* Symbiotic 10 participating in [SV-COMP 2024](https://sv-comp.sosy-lab.org/2024/results/results-verified/), compiled version available at [Zenodo](https://zenodo.org/records/10202594)
  * 2nd in MemSafety
  * 2nd in FalsificationOverall
* Symbiotic 10 participating in [Test-Comp 2024](https://test-comp.sosy-lab.org/2024/results/results-verified/), compiled version available at [Zenodo](https://zenodo.org/records/10202594)
  * 3rd in Cover-Error
* Symbiotic 9.1 participating in [SV-COMP 2023](https://sv-comp.sosy-lab.org/2023/results/results-verified/), compiled version available at [Zenodo](https://zenodo.org/record/7622656#.Y-P7YnbMKUk)
  * 1st in MemSafety 
  * 1st in SoftwareSystems
* Symbiotic 9 participating in [SV-COMP 2022](https://sv-comp.sosy-lab.org/2022/results/results-verified/)
  * **1st in Overall**
  * 1st in MemSafety 
  * 1st in SoftwareSystems
  * 3rd in FalsificationOverall
* Symbiotic 8 participating in [SV-COMP 2021](https://sv-comp.sosy-lab.org/2021/results/results-verified/)
  * 1st in MemSafety 
  * 1st in SoftwareSystems
* Symbiotic 8 participating in [Test-Comp 2021](https://test-comp.sosy-lab.org/2021/results/results-verified/)
  * 3rd in Cover-Branches
* Symbiotic 7 participating in [SV-COMP 2020](https://sv-comp.sosy-lab.org/2020/results/results-verified/)
  * 1st in SoftwareSystems
  * 2nd in MemSafety 
  * 2nd in FalsificationOverall
* Symbiotic 6 participating in [SV-COMP 2019](https://sv-comp.sosy-lab.org/2019/results/results-verified/)
  * 1st in MemSafety 
* Symbiotic 5 participating in [SV-COMP 2018](https://sv-comp.sosy-lab.org/2018/results/results-verified/)
  * 1st in MemSafety 
  * 3rd in FalsificationOverall
* Symbiotic 4 participating in [SV-COMP 2017](https://sv-comp.sosy-lab.org/2017/results/results-verified/)
  * 3rd in MemSafety 
* Symbiotic 3 participating in [SV-COMP 2016](https://sv-comp.sosy-lab.org/2016/results/results-verified/)
  * 3rd in Arrays

## Publications

1. J. Slaby, J. Strejček, and M. Trtík: _Checking Properties Described by State Machines: On Synergy of Instrumentation, Slicing, and Symbolic Execution_, in Proceedings of FMICS 2012, volume 7437 of LNCS, pages 207-221. Springer, 2012. \[[link](http://is.muni.cz/repo/984069/sse.pdf)\]

2. J. Slaby, J. Strejček, and M. Trtík: _Symbiotic: Synergy of Instrumentation, Slicing, and Symbolic Execution (Competition Contribution)_, in Proceedings of TACAS 2013, volume 7795 of LNCS, pages 630-632. Springer, 2013. \[[link](https://www.fi.muni.cz/~xstrejc/publications/tacas2013preprint.pdf)\]

3. J. Slaby and J. Strejček: _Symbiotic 2: More Precise Slicing (Competition Contribution)_, in Proceedings of TACAS 2014, volume 8413 of LNCS, pages 415-417. Springer, 2014. \[[link](https://www.fi.muni.cz/~xstrejc/publications/tacas2014preprint.pdf)\]

4. M. Chalupa, M. Jonáš, J. Slaby, J. Strejček, and M. Vitovská: _Symbiotic 3: New Slicer and Error-Witness Generation (Competition Contribution)_, in Proceedings of TACAS 2016, volume 9636 of LNCS, pages 946-949. Springer, 2016. \[[link](https://www.fi.muni.cz/~xstrejc/publications/tacas2016symbiotic_preprint.pdf)\]

5. M. Chalupa, M. Vitovská, M. Jonáš, J. Slaby, and J. Strejček: _Symbiotic 4: Beyond Reachability (Competition Contribution)_, in Proceedings of TACAS 2017, volume 10206 of LNCS, pages 385-389. Springer, 2017. \[[link](https://www.fi.muni.cz/~xstrejc/publications/tacas2017preprint.pdf)\]

6. M. Chalupa, M. Vitovská, and J. Strejček: _Symbiotic 5: Boosted Instrumentation (Competition Contribution)_, in Proceedings of TACAS 2018, volume 10806 of LNCS, pages 442-226. Springer, 2018. \[[link](https://link.springer.com/chapter/10.1007/978-3-319-89963-3_29)\]

7. M. Chalupa, M. Vitovská, T. Jašek, M. Šimáček, and J. Strejček: _Symbiotic 6: Generating Test-Cases by Slicing and Symbolic Execution_, International Journal on Software Tools for Technology Transfer 23(6): 875-877, 2021. \[[link](https://www.fi.muni.cz/~xstrejc/publications/sttt2020preprint.pdf)\]

8. M. Chalupa, T. Jašek, L. Tomovič, M. Hruška, V. Šoková, P. Ayaziová, J. Strejček, and T. Vojnar: _Symbiotic 7: Integration of Predator and More (Competition Contribution)_, in Proceedings of TACAS 2020, volume 12079 of LNCS, pages 413-417. Springer, 2020. \[[link](https://link.springer.com/chapter/10.1007/978-3-030-45237-7_31)\]

9. M. Chalupa, T. Jašek, J. Novák, A. Řechtáčková, V. Šoková, and J. Strejček: _Symbiotic 8: Beyond Symbolic Execution (Competition Contribution)_, in Proceedings of TACAS 2021, volume 12652 of LNCS, pages 453-457. Springer, 2021. \[[link](https://link.springer.com/chapter/10.1007/978-3-030-72013-1_31)\] 

10. M. Chalupa, J. Novák, and J. Strejček: _Symbiotic 8: Parallel and Targeted Test Generation (Competition Contribution)_, in Proceedings of FASE 2021, volume 12649 of LNCS, pages 368-372. Springer, 2021. \[[link](https://link.springer.com/chapter/10.1007/978-3-030-71500-7_20)\]

11. M. Chalupa, V. Mihalkovič, A. Řechtáčková, L. Zaoral, and J. Strejček: _Symbiotic 9: String Analysis and Backward Symbolic Execution with Loop Folding (Competition Contribution)_, in Proceedings of TACAS 2022, volume 13244 of LNCS, pages 462-467. Springer, 2022. \[[link](https://link.springer.com/chapter/10.1007/978-3-030-99527-0_32)\]

12. M. Jonáš, K. Kumor, J. Novák, J. Sedláček, M. Trtík, L. Zaoral, P. Ayaziová, and J. Strejček: _Symbiotic 10: Lazy Memory Initialization and Compact Symbolic Execution (Competition Contribution)_, in Proceedings of TACAS 2024, volume 14572 of LNCS, pages 406-411. Springer, 2024. \[[link](https://link.springer.com/chapter/10.1007/978-3-031-57256-2_29)\]

## Contact

For more information send an e-mail to <statica@fi.muni.cz>. We'll be happy to answer your questions :)
