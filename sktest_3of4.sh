function cleanup()
{
    pkill -9 -f restarting_skaled
    pkill -9 -f kill4
    pkill -f skaled
    exit
}
trap cleanup SIGINT SIGTERM SIGHUP EXIT

./kill4.sh&
export ORIGINAL_SKALED=$SKTEST_EXE
NUM_NODES=4 NO_ULIMIT_CHECK=1 SKTEST_EXE=./restarting_skaled.sh python3 -u sktest_performance.py || true
