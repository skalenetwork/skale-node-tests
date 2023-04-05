RET=0
cleanup () {
    pkill -9 -f restarting_skaled
    pkill -f skaled
    echo Func exiting $RET
    exit $RET
}
#trap cleanup INT TERM HUP EXIT

./kill4.sh&
KILL4_PID=$!
export ORIGINAL_SKALED=$SKTEST_EXE
NUM_NODES=4 NO_ULIMIT_CHECK=1 SKTEST_EXE=./restarting_skaled.sh python3 -u sktest_performance.py
RET=$?

#kill $KILL4_PID
#wait

echo Exiting $RET
exit $RET
