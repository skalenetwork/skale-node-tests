#!/bin/bash

N=$1

if [[ ! $N -gt 0 ]]
then
  echo "USAGE $0 <N>"
  exit
fi

for (( i=1; i<=$N; i++ ))
do
#	echo "$i/$N" >$i.gfn
	cp 4kdata $i.gfn
done
