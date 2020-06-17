#!/usr/bin/env bash

set -e

: "${LVMPY_REPO?Need to set LVMPY_REPO}"
: "${SKALED_REPO?Need to set SKALED_REPO}"
: "${SKALED_BINARY?Need to set SKALED_REPO}"

BASE_DIR=$PWD

IMAGE_NAME='skalenetwork/schain:test'
SKALED_BUILD_DIR=$SKALED_REPO/scripts/skale_build

echo 'Preparing schain image'
if [ ! -f $SKALED_BUILD_DIR/executable/skaled ]; then
    cp $SKALED_BINARY $SKALED_BUILD_DIR/executable/skaled
fi
cd $SKALED_BUILD_DIR
echo "Building $IMAGE_NAME..."
docker build -t $IMAGE_NAME .

cd $BASE_DIR
echo 'Creating loopback block device'
dd if=/dev/zero of=loopbackfile.img bs=400M count=10
losetup -fP loopbackfile.img
losetup -a
echo 'Block device created from file'
BLOCK_DEVICE="$(losetup --list -a | grep loopbackfile.img |  awk '{print $1}')"

echo 'Installing lvmpy volume driver'
cd $LVMPY_REPO
BLOCK_DEVICE=/dev/loop5
VOLUME_GROUP=schains PHYSICAL_VOLUME=$BLOCK_DEVICE sudo -E scripts/install.sh
