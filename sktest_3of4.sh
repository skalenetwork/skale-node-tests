set -x
RET=0
cleanup () {
	trap '' INT TERM HUP EXIT
	kill $KILL4_PID
    pkill -f restarting_skaled
#    pkill -f skaled
#    pkill -f skaled
	wait
    echo Func exiting $RET
    exit $RET
}
trap cleanup INT TERM HUP EXIT

./kill4.sh&
KILL4_PID=$!
export ORIGINAL_SKALED=$SKTEST_EXE
NUM_NODES=4 NO_ULIMIT_CHECK=1 SKTEST_EXE=./restarting_skaled.sh python3 -u sktest_performance.py
RET=$?

echo Exiting $RET
exit $RET
