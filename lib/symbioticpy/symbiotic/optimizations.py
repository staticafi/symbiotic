#!/usr/bin/python


optimizations = {
    'conservative':
    ['-simplifycfg', '-constmerge', '-dce', '-ipconstprop', '-argpromotion',
     '-instcombine', '-deadargelim', '-simplifycfg'],

    # the list of optimizations is based on klee -optimize
    # option, but is adjusted for our needs (therefore
    # we don't use the -optimize option with klee)
    'klee':
    ['-simplifycfg', '-globalopt', '-globaldce', '-ipconstprop',
     '-deadargelim', '-instcombine', '-simplifycfg', '-prune-eh',
     '-functionattrs',
     # if we inline too much, then the analysis take too long and
     # witnesses are useless (default is 255)
     '-inline-threshold=70',
     '-inline', '-argpromotion', '-instcombine',
     '-jump-threading', '-simplifycfg', '-gvn', '-scalarrepl',
     '-instcombine', '-tailcallelim', '-simplifycfg',
     '-reassociate', '-loop-rotate', '-licm', '-loop-unswitch',
     '-instcombine', '-indvars', '-loop-deletion', '-loop-unroll',
     '-instcombine', '-memcpyopt', '-sccp', '-instcombine',
     '-dse', '-adce', '-simplifycfg', '-strip-dead-prototypes',
     '-constmerge', '-ipsccp', '-deadargelim', '-die',
     '-instcombine'],

    # -O3 optimizations list from opt 3.8 without the vectorizers
    'O3':
    ['-tti', '-targetlibinfo', '-tbaa', '-scoped-noalias',
     '-assumption-cache-tracker', '-verify', '-simplifycfg', '-domtree',
     '-sroa',
     '-early-cse', '-lower-expect',
     '-targetlibinfo', '-tti', '-tbaa', '-scoped-noalias',
     '-assumption-cache-tracker', '-forceattrs', '-inferattrs', '-ipsccp',
     '-globalopt', '-domtree',
     '-mem2reg',
     '-deadargelim', '-basicaa', '-aa',
     '-domtree', '-instcombine', '-simplifycfg', '-basiccg', '-globals-aa',
     '-prune-eh',
     # if we inline too much, then the analysis take too long and
     # witnesses are useless (default is 255)
     '-inline-threshold=70',
     '-inline', '-functionattrs', '-argpromotion', '-domtree',
     '-sroa',
     '-early-cse', '-lazy-value-info', '-jump-threading',
     '-correlated-propagation', '-simplifycfg', '-basicaa', '-aa', '-domtree',
     '-instcombine', '-tailcallelim', '-simplifycfg', '-reassociate', '-domtree',
     '-loops', '-loop-simplify', '-lcssa',
     # TODO
     # loop-rotate here makes use to incorrectly answer
     # SpamAssassin-loop_true-unreach-call_false-termination.i benchmark
     # I do not know where is the problem (maybe also in the benchmark?)
     # but moving loop-rotate after loop-unswitch fixes it. Do not have time
     # to look into that now (so I won't probably do that ever)
     # '-loop-rotate',
     '-basicaa', '-aa',
     '-licm', '-loop-unswitch',
     # OK, do not use loop-rotate at all, it transforms the loops in the way
     # that we can not handle because we use the Ferrante's CD algorithm
     #'-loop-rotate',
     '-simplifycfg', '-basicaa', '-aa', '-domtree',
     '-instcombine', '-loops', '-scalar-evolution', '-loop-simplify', '-lcssa',
     '-indvars', '-aa', '-loop-idiom', '-loop-deletion', '-loop-unroll',
     '-basicaa', '-aa', '-mldst-motion', '-aa', '-memdep', '-gvn', '-basicaa',
     '-aa', '-memdep', '-memcpyopt', '-sccp', '-domtree', '-demanded-bits',
     '-bdce', '-basicaa', '-aa', '-instcombine', '-lazy-value-info',
     '-jump-threading', '-correlated-propagation', '-domtree', '-basicaa',
     '-aa', '-memdep', '-dse', '-loops', '-loop-simplify', '-lcssa', '-aa',
     '-licm', '-adce', '-simplifycfg', '-basicaa', '-aa', '-domtree',
     '-instcombine', '-barrier', '-basiccg', '-rpo-functionattrs',
     '-elim-avail-extern', '-basiccg', '-globals-aa', '-float2int', '-domtree',
     '-loops',
     '-loop-simplify', '-lcssa',
     # loop-rotate here leads to loops that we can not slice correctly because
     # we use the Ferrante's control dependencies
     # '-loop-rotate',
     '-branch-prob',
     '-block-freq', '-scalar-evolution', '-basicaa', '-aa', '-loop-accesses',
     '-demanded-bits',
     #    #'-loop'-vectorize',
     '-instcombine', '-scalar-evolution', '-aa',
     #    # '-slp-vectorizer',
     '-simplifycfg', '-basicaa', '-aa', '-domtree', '-instcombine', '-loops',
     '-loop-simplify', '-lcssa', '-scalar-evolution', '-loop-unroll', '-basicaa',
     '-aa', '-instcombine', '-loop-simplify', '-lcssa', '-aa', '-licm',
     '-scalar-evolution', '-alignment-from-assumptions',
     '-strip-dead-prototypes', '-globaldce', '-constmerge', '-verify'],

    # -O2 optimizations list from opt 3.8 without the vectorizers
    'O2':
    ['-tti', '-targetlibinfo', '-tbaa', '-scoped-noalias',
     '-assumption-cache-tracker', '-verify', '-simplifycfg', '-domtree',
     '-sroa', '-early-cse', '-lower-expect',
     '-targetlibinfo', '-tti', '-tbaa', '-scoped-noalias',
     '-assumption-cache-tracker', '-forceattrs', '-inferattrs', '-ipsccp',
     '-globalopt', '-domtree', '-mem2reg', '-deadargelim', '-basicaa', '-aa',
     '-domtree', '-instcombine', '-simplifycfg', '-basiccg', '-globals-aa',
     '-prune-eh', '-inline', '-functionattrs',
     #'-argpromotion',
     '-domtree', '-sroa', '-early-cse', '-lazy-value-info', '-jump-threading',
     '-correlated-propagation', '-simplifycfg', '-basicaa', '-aa', '-domtree',
     '-instcombine', '-tailcallelim', '-simplifycfg', '-reassociate', '-domtree',
     '-loops', '-loop-simplify', '-lcssa', '-loop-rotate', '-basicaa', '-aa',
     '-licm', '-loop-unswitch', '-simplifycfg', '-basicaa', '-aa', '-domtree',
     '-instcombine', '-loops', '-scalar-evolution', '-loop-simplify', '-lcssa',
     '-indvars', '-aa', '-loop-idiom', '-loop-deletion', '-loop-unroll',
     '-basicaa', '-aa', '-mldst-motion', '-aa', '-memdep', '-gvn', '-basicaa',
     '-aa', '-memdep', '-memcpyopt', '-sccp', '-domtree', '-demanded-bits',
     '-bdce', '-basicaa', '-aa', '-instcombine', '-lazy-value-info',
     '-jump-threading', '-correlated-propagation', '-domtree', '-basicaa',
     '-aa', '-memdep', '-dse', '-loops', '-loop-simplify', '-lcssa', '-aa',
     '-licm', '-adce', '-simplifycfg', '-basicaa', '-aa', '-domtree',
     '-instcombine', '-barrier', '-basiccg', '-rpo-functionattrs',
     '-elim-avail-extern', '-basiccg', '-globals-aa', '-float2int', '-domtree',
     '-loops', '-loop-simplify', '-lcssa', '-loop-rotate', '-branch-prob',
     '-block-freq', '-scalar-evolution', '-basicaa', '-aa', '-loop-accesses',
     '-demanded-bits',
     #'-loop'-vectorize',
     '-instcombine', '-scalar-evolution', '-aa',
     # '-slp-vectorizer',
     '-simplifycfg', '-basicaa', '-aa', '-domtree', '-instcombine', '-loops',
     '-loop-simplify', '-lcssa', '-scalar-evolution', '-loop-unroll', '-basicaa',
     '-aa', '-instcombine', '-loop-simplify', '-lcssa', '-aa', '-licm',
     '-scalar-evolution', '-alignment-from-assumptions',
     '-strip-dead-prototypes', '-globaldce', '-constmerge', '-verify']
}
