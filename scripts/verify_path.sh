DIR=`dirname $0`
KLEE_OUTPUT_DIR="$1"

get_path_file()
{
	KLEE_OUTPUT_DIR="$1"
	FILE=`ls $KLEE_OUTPUT_DIR | grep assert.err`
	echo "${FILE%.assert.err}.path"
}

PRPFILE="$2"
BENCHMARK="$3"
BENCHMARKDIR=`dirname "$BENCHMARK"`
PTH="$KLEE_OUTPUT_DIR/`get_path_file $KLEE_OUTPUT_DIR`"
GRAPHML="${PTH%.path}.graphml"

if [ ! -f "$PTH" ]; then
	echo "Failed getting .path file"
	exit 1
fi

# convert path file to .graphml
$DIR/path_to_ml.pl "$PTH" > "$GRAPHML" || exit 1
if [ ! -f "$GRAPHML" ]; then
	echo "Failed generating .graphml file"
	exit 1
fi

test -z $CPA && CPA="$DIR/CPAchecker/scripts/cpa.sh"
CPADIR=`dirname $CPA`

cd $CPADIR/.. || exit 1
STATUS=$(scripts/cpa.sh -noout -heap 10000M -predicateAnalysis \
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
"$BENCHMARK" 2>&1 | if grep -q 'Error path found and confirmed'; then echo "confirmed"; fi)

if [ $? -ne 0 ]; then
	STATUS="error"
elif [ "$STATUS" != "confirmed" ]; then
	STATUS="unconfirmed"
fi

echo "$STATUS"
