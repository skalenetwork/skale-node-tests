#!/bin/bash
INTERVAL=30
let i=1			# iterates through all
#let j=1			# iterates 4 times slower
#let k=2			# whom to kill
while :
do

sleep $INTERVAL

echo Killing $((i+1))
pkill -9 -f "/skaled .*/$((i+1))"

#if [[ $j == '0' && ( ($i != '1' || $k != '2') && ($i != '2' || $k != '1') ) ]]
#then
#    sleep 10
#    echo Killing $k
#    kill -9 `pgrep -f "skaled/skaled.*/$k"`
#    let "k=(k%4)+1"
#fi

let "i=(i%3)+1"
#let "j=(j+1)%3"
done

