DIR=`dirname $0`

#FIXME move this script to satt,
# it has nothing in common with this repository

GRAPHML="$1"
PRPFILE="$2"
BENCHMARK="$3"
VERIFIER_RESULT="$GRAPHML.result"

BENCHMARKDIR=`dirname "$BENCHMARK"`

test -z $CPA && CPA="$DIR/CPAchecker/scripts/cpa.sh"
CPADIR=`dirname $CPA`

cd $CPADIR/.. || exit 1
(scripts/cpa.sh -noout -heap 10000M -predicateAnalysis \
-setprop cfa.useMultiEdges=false \
-setprop cpa.predicate.solver=MATHSAT5 \
-setprop cfa.simplifyCfa=false \
-setprop cfa.allowBranchSwapping=false \
-setprop cpa.predicate.ignoreIrrelevantVariables=false \
-setprop counterexample.export.assumptions.assumeLinearArithmetics=true \
-setprop coverage.enabled=false \
-setprop coverage.mode=TRANSFER \
-setprop coverage.export=true \
-setprop analysis.traversal.byAutomatonVariable=__DISTANCE_TO_VIOLATION \
-setprop cpa.automaton.treatErrorsAsTargets=false \
-setprop WitnessAutomaton.cpa.automaton.treatErrorsAsTargets=true \
-setprop parser.transformTokensToLines=false \
-setprop spec.matchOriginLine=true \
-setprop spec.matchOffset=true \
-setprop spec.matchAssumeCase=true \
-setprop spec.matchSourcecodeData=false \
-setprop spec.strictMatching=false \
-setprop cpa.composite.inCPAEnabledAnalysis=true \
-setprop cpa.predicate.handlePointerAliasing=false \
-skipRecursion \
-spec "$GRAPHML" \
-spec "$PRPFILE" \
"$BENCHMARK") 1>/dev/null 2>"$VERIFIER_RESULT"

if [ $? -ne 0 ]; then
	echo "error"
elif grep -q 'Error path found and confirmed' "$VERIFIER_RESULT"; then
	echo "confirmed"
else
	echo "unconfirmed"
fi

echo "=== WITNESS OUTPUT"
cat "$VERIFIER_RESULT"
echo "--- WITNESS ---"
cat "$GRAPHML"

rm "$VERIFIER_RESULT"
