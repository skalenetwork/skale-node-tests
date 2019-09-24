#!/bin/bash
EXE=~/skaled/build-no-mp/skaled/skaled
trap -- '' SIGINT SIGTERM SIGHUP EXIT
until $EXE $@; do
	echo "Restarting $EXE $@"
	sleep 5
done
