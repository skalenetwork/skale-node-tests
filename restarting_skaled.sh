#!/bin/bash
EXE=~/skaled/build-no-mp-no-tsan/skaled/skaled
trap -- '' SIGTERM SIGHUP SIGINT
until $EXE $@; do
#while :; do
#	$EXE $@
	echo "Restarting $EXE $@"
	sleep 5
done
