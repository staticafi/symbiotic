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

def gentest(bitcode, outdir, prp, suffix=None, params=None):
    options = ['-use-forked-solver=0', '--use-call-paths=0',
               '--output-stats=0', '-istats-write-interval=60s',
               '-timer-interval=10', '-external-calls=pure',
               '-write-testcases', '-malloc-symbolic-contents',
               '-max-memory=8000', '-output-source=false']
    if prp != 'coverage':
        options.append(f'-error-fn={prp}')
        options.append('-exit-on-error-type=Assert')
        options.append('-dump-states-on-halt=0')
    else:
        options.append('-only-output-states-covering-new=1')
        options.append('-max-time=840')

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
    if p.poll() != 0:
        print(errs)
        print(out)
        return None, None
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

def check_error(outs, errs):
    for line in outs.splitlines():
        if b'ASSERTION FAIL: ' in line:
            print('Found ERROR!', file=stderr)
            return True
    return False

def main(argv):
    if len(argv) != 4:
        exit(1)
    prp = argv[1]
    outdir = argv[2]
    bitcode = argv[3]

    generators = []

    # run KLEE on the original bitcode
    print("\n--- Running the main KLEE --- ", file=stderr)
    maingen = gentest(bitcode, outdir, prp)
    if maingen:
        generators.append(maingen)

    bitcodewithcrits, crits = find_criterions(bitcode)
    if bitcodewithcrits:
        # The later crits are likely deeper in the code.
        # Since run use only part of them, use those.
        crits = list(crits)
        crits.reverse()
        for n, crit in enumerate(crits):
            print(f"\n--- Targeting at {crit} target --- ", file=stderr)
            if prp == 'coverage' and maingen and maingen.poll() is not None:
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
            if prp == 'coverage' and maingen and maingen.poll() is not None:
                break # the main process finished, we can finish too
            p = gentest(slicedcode, outdir, prp, suffix=str(n),
                        params=['--search=dfs', '--use-batching-search'])
            if p is None:
                continue
            generators.append(p)

            newgens = []
            for p in generators:
                if p.poll() is not None:
                    if prp != 'coverage':
                        if check_error(*p.communicate()):
                            for gen in generators:
                                if gen.poll() is not None:
                                    gen.kill()
                            exit(0)
                else:
                    newgens.append(p)
            generators = newgens

            # run atmost 8 at once
            while len(generators) >= 8:
                if prp == 'coverage' and maingen and maingen.poll() is not None:
                    break # the main process finished, we can finish too

                print("Got enough test generators, waiting for some to finish...",
                      file=stderr)
                sleep(2) # sleep 2 seconds
                for p in generators:
                    if p.poll() is not None:
                        if prp != 'coverage':
                            if check_error(*p.communicate()):
                                for gen in generators:
                                    if gen.poll() is not None:
                                        gen.kill()
                                exit(0)
                    else:
                        newgens.append(p)
                # some processes finished
                generators = newgens

    print(f"\n--- All targets running --- ", file=stderr)
    stderr.flush()

    while generators:
        print(f"Have {len(generators)} test generators running", file=stderr)
        stderr.flush()
        newgens = []
        for p in generators:
            if p.poll() is not None:
                if prp != 'coverage':
                    if check_error(*p.communicate()):
                        for gen in generators:
                            if gen.poll() is not None:
                                gen.kill()
                        exit(0)
            else:
                newgens.append(p)
        generators = newgens
        if generators:
            sleep(2) # sleep 2 seconds

    print(f"\n--- All KLEE finished --- ", file=stderr)

    if prp == 'coverage':
        # if all finished, then also the main KLEE finished,
        # and we can remove the files from side KLEE's -- those
        # are superfluous
        runcmd(['rm', '-f', f"{outdir}/test*.*.xml"])

if __name__ == "__main__":
    from sys import argv
    main(argv)
