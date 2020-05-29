./kill4.sh&
NUM_NODES=4 SKTEST_EXE=./restarting_skaled.sh python3 -u -i sktest_performance.py || true
pkill -9 -f restarting_skaled
pkill -9 -f kill4
