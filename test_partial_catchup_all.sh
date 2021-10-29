#!/bin/bash
#run with sudo

export NO_ULIMIT_CHECK=1
export DATA_DIR=btrfs
export BTRFS_DIR_PATH=btrfs
export SKTEST_EXE=/home/dimalit/skaled/build/skaled/skaled

CMD() {
	echo Running test case $1
	../skaled-debug/create_btrfs.sh
	python3 -m pytest -s $1
}

# abort on 1st error
set -e

CMD 'test_partial_catchup.py::test_basic[OverlayDB_commit_2]'
CMD 'test_partial_catchup.py::test_basic[insertBlockAndExtras]'
CMD 'test_partial_catchup.py::test_basic[after_remove_oldest]'
CMD 'test_partial_catchup.py::test_basic[with_two_keys]'
CMD 'test_partial_catchup.py::test_basic[with_two_keys_2]'
CMD 'test_partial_catchup.py::test_basic[genesis_after_rotate]'
CMD 'test_partial_catchup.py::test_basic[after_genesis_after_rotate]'

CMD 'test_partial_catchup.py::test_repair[after_pieces_kill]'
CMD 'test_partial_catchup.py::test_repair[after_recover]'
CMD 'test_partial_catchup.py::test_repair[fix_bad_rotation]'
CMD 'test_partial_catchup.py::test_repair[insertBlockAndExtras]'
