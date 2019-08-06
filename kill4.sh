#!/bin/bash
INTERVAL=22
let i=2			# iterates through all
let j=1			# iterates 4 times slower
let k=2			# whom to kill
while :
do

sleep $INTERVAL

echo Killing $i
kill -9 `pgrep -f "skaled/skaled.*/$i"`

if [[ $j == '0' && ( ($i != '1' || $k != '2') && ($i != '2' || $k != '1') ) ]]
then
    echo Killing $k
    kill -9 `pgrep -f "skaled/skaled.*/$k"`
    let "k=(k%4)+1"
fi

let "i=(i%4)+1"
let "j=(j+1)%3"
done

