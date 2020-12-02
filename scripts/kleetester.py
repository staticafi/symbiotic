#!/usr/bin/python3
from subprocess import Popen, PIPE, STDOUT
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

def sliceprocess(bitcode, crit):
    slbitcode = f"{bitcode}-{crit}.bc"
    cmd = ['timeout', '120', 'llvm-slicer', '-c', crit,
           '-o', slbitcode, bitcode]

    return runcmd(cmd), slbitcode

def gentest(bitcode, outdir, suffix=None):
    options = ['-use-forked-solver=0', '--use-call-paths=0',
               '--output-stats=0', '-istats-write-interval=60s',
               '-timer-interval=10', '-external-calls=pure',
               '-write-testcases', '-malloc-symbolic-contents',
               '-max-memory=8000', '-only-output-states-covering-new=1',
               '-max-time=840', '-output-source=false']

    cmd = ['klee', f'-output-dir={outdir}']
    if suffix:
        cmd.append(f'-testcases-suffix={suffix}')
    cmd.extend(options)
    cmd.append(bitcode)

    return runcmd(cmd)

def find_criterions(bitcode):
    newbitcode = f"{bitcode}.tpr.bc"
    cmd = ['opt', '-load', 'LLVMsbt.so', '-get-test-targets',
           '-o', newbitcode, bitcode]
    p = runcmd(cmd)
    if p is None:
        return None, None
    out, errs = p.communicate()
    if out and out != '':
        return newbitcode, (crit.decode('utf-8', 'ignore') for crit in out.splitlines())
    return None, None

def optimize(bitcode):
    newbitcode = f"{bitcode}.opt.bc"
    cmd = ['opt', '-load', 'LLVMsbt.so', '-O3', '-remove-infinite-loops',
           '-O2', '-o', newbitcode, bitcode]
    p = runcmd(cmd)
    ret = p.wait()
    if ret != 0:
        out, errs = p.communicate()
        print(out, file=stderr)
        print(errs, file=stderr)
        return None
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
        n = 0
        for crit in crits:
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
            n += 1
            p = gentest(slicedcode, outdir, suffix=str(n))
            if p is None:
                continue
            generators.append(p)

            if n > 15: # Do not run more of these processes
                break

    print(f"\n--- All targets running --- ", file=stderr)
    stderr.flush()

    # wait until the main test generator finishes
    if maingen:
        maingen.wait()
        print(f"\n--- Main KLEE finished --- ", file=stderr)
    # kill side generators (or wait for them if there is no main)
    for p in generators:
        if maingen:
            if p.poll() is not None:
                p.kill()
        else:
            p.wait()
    print(f"\n--- All KLEE finished --- ", file=stderr)


if __name__ == "__main__":
    from sys import argv
    main(argv)
