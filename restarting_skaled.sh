#!/bin/bash
EXE=~/skaled/build-no-mp/skaled/skaled
trap -- '' SIGINT SIGTERM SIGHUP EXIT
#until $EXE $@; do
while true; do
	$EXE $@
	echo "Restarting $EXE $@"
	sleep 1
done
