#!/usr/bin/python3
from subprocess import Popen, PIPE, STDOUT
from time import sleep
from sys import stderr

def runcmd(cmd):
    print("[kleetester] {0}".format(" ".join(cmd)), file=stderr)
    stderr.flush()

    try:
        p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
    except OSError as e:
        print(str(e), file=stderr)
        return None

    return p

def gentest(bitcode, outdir, suffix=None, params=None):
    options = ['-use-forked-solver=0', '--use-call-paths=0',
               '--output-stats=0', '-istats-write-interval=60s',
               '-timer-interval=10', '-external-calls=pure',
               '-write-testcases', '-malloc-symbolic-contents',
               '-max-memory=8000', '-only-output-states-covering-new=1',
               '-max-time=840', '-output-source=false']
    if params:
        options.extend(params)

    cmd = ['klee', f'-output-dir={outdir}']
    if suffix:
        cmd.append(f'-testcases-suffix={suffix}')
    cmd.extend(options)
    cmd.append(bitcode)

    return runcmd(cmd)

def find_criterions(bitcode):
    newbitcode = f"{bitcode}.tpr.bc"
    # FIXME: generate it directly from slicer (multiple slices)
    # FIXME: modify the code also such that any path that avoids the criterion
    # is aborted
    cmd = ['opt', '-load', 'LLVMsbt.so', '-get-test-targets',
           '-o', newbitcode, bitcode]
    p = runcmd(cmd)
    if p is None:
        return None, None
    out, errs = p.communicate()
    if out and out != '':
        return newbitcode, (crit.decode('utf-8', 'ignore') for crit in out.splitlines())
    return None, None

def constrain_to_target(bitcode, target):
    newbitcode = f"{bitcode}.opt.bc"
    cmd = ['opt', '-load', 'LLVMsbt.so', '-constraint-to-target',
           f'-ctt-target={target}', '-O3', '-o', newbitcode, bitcode]
    p = runcmd(cmd)
    if p is None:
        return None
    ret = p.wait()
    if ret != 0:
        out, errs = p.communicate()
        print(out, file=stderr)
        print(errs, file=stderr)
        return None
    return newbitcode

def sliceprocess(bitcode, crit):
    bitcode = constrain_to_target(bitcode, crit)
    if bitcode is None:
        return None, None
        
    slbitcode = f"{bitcode}-{crit}.bc"
    cmd = ['timeout', '120', 'llvm-slicer', '-c', crit,
           '-o', slbitcode, bitcode]
    return runcmd(cmd), slbitcode

def optimize(bitcode):
    newbitcode = f"{bitcode}.opt.bc"
    cmd = ['opt', '-load', 'LLVMsbt.so', '-O3', '-remove-infinite-loops',
           '-O2', '-o', newbitcode, bitcode]
    p = runcmd(cmd)
    ret = p.wait()
    return newbitcode

def main(argv):
    if len(argv) != 3:
        exit(1)
    outdir = argv[1]
    bitcode = argv[2]

    generators = []

    # run KLEE on the original bitcode
    print("\n--- Running the main KLEE --- ", file=stderr)
    maingen = gentest(bitcode, outdir)

    bitcodewithcrits, crits = find_criterions(bitcode)
    if bitcodewithcrits:
        # The later crits are likely deeper in the code.
        # Since run use only part of them, use those.
        crits = list(crits)
        crits.reverse()
        for n, crit in enumerate(crits):
            print(f"\n--- Targeting at {crit} target --- ", file=stderr)
            if maingen and maingen.poll() is not None:
                break # the main process finished, we can finish too

            # slice bitcode
            p, slicedcode = sliceprocess(bitcodewithcrits, crit)
            if p is None:
                print(f'Slicing w.r.t {crit} FAILED', file=stderr)
                continue
            print(f'Starget slicing w.r.t {crit}, waiting for the job...', file=stderr)
            ret = p.wait()
            if ret != 0:
                out, errs = p.communicate()
                print(f'Slicing w.r.t {crit} FAILED', file=stderr)
                if ret == 124:
                    break # one timeouted, others will too...
                print(out, file=stderr)
                print(errs, file=stderr)
                continue
            print(f'Slicing w.r.t {crit} done', file=stderr)

            slicedcode = optimize(slicedcode)
            if slicedcode is None:
                print("Optimizing failed", file=stderr)
                continue

            # generate tests
            if maingen and maingen.poll() is not None:
                break # the main process finished, we can finish too
            p = gentest(slicedcode, outdir, suffix=str(n),
                        params=['--search=dfs', '--use-batching-search'])
            if p is None:
                continue
            generators.append(p)

            # FIXME: run atmost 8 at once
            while len(generators) >= 7:
                if maingen and maingen.poll() is not None:
                    break # the main process finished, we can finish too
                print("Got enough test generators, waiting for some to finish...",
                      file=stderr)
                sleep(2) # sleep 2 seconds
                newgens = [p for p in generators if p.poll() is None]
                # some processes finished
                if len(newgens) != len(generators):
                    generators = newgens


    print(f"\n--- All targets running --- ", file=stderr)
    stderr.flush()

    # wait until the main test generator finishes
    main_finished = False
    if maingen:
        maingen.wait()
        print(f"\n--- Main KLEE finished --- ", file=stderr)
        main_finished = True
    # kill side generators (or wait for them if there is no main)
    for p in generators:
        if maingen:
            if p.poll() is not None:
                p.kill()
        else:
            p.wait()
    print(f"\n--- All KLEE finished --- ", file=stderr)

    if main_finished:
        # if main KLEE finished, remove the files from side KLEE's -- those
        # are superfluous
        runcmd(['rm', '-f', f"{outdir}/test*.*.xml"])

if __name__ == "__main__":
    from sys import argv
    main(argv)
