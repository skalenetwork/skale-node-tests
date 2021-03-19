#!/bin/bash
EXE=${ORIGINAL_SKALED:-~/skaled/build-debug-release/skaled/skaled}
#trap -- '' SIGINT SIGTERM SIGHUP EXIT
#until $EXE $@; do
while true; do
	$EXE $@
	echo "Restarting $EXE $@"
	sleep 1
done
