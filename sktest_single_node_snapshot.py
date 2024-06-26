import os
import time
from time import sleep
from sktest import LocalStarter, Node, SChain

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

global sktest_exe
sktest_exe = os.getenv("SKTEST_EXE",
                       "/home/dimalit/skaled/build-no-mp/skaled/skaled")

emptyBlockIntervalMs = 2000
snapshotIntervalSec = 10

run_container = os.getenv('RUN_CONTAINER')

node = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec)
starter = LocalStarter(sktest_exe)

ch = SChain(
    [node],
    starter,
    prefill=[1000000000000000000, 2000000000000000000],
    emptyBlockIntervalMs=emptyBlockIntervalMs,
    snapshotIntervalSec=snapshotIntervalSec
)
ch.start(start_timeout=60)

print("Waiting for snapshots to be done")

snapshots_count = 0
latest_snapshot_block = 0

while True:
    bn = node.eth.blockNumber

    print(f"blockNumber is: {bn}")

    current_latest = node.eth.getLatestSnapshotBlockNumber()

    print(f"Latest snapshot block: {current_latest}")

    if latest_snapshot_block != current_latest:
        latest_snapshot_block = current_latest
        snapshots_count += 1

    print(f"Snapshots done: {snapshots_count}")

    if snapshots_count > 5:
        break

    time.sleep(0.6)

print("Exiting")

ch.stop_without_cleanup()

print("Restarting skaled")

ch.start_after_stop(start_timeout=90)

print("Waiting for snapshots to be done after restart")

snapshots_done_after_restart = 0

while True:
    bn = node.eth.blockNumber

    print(f"blockNumber is: {bn}")

    current_latest = node.eth.getLatestSnapshotBlockNumber()

    print(f"Latest snapshot block: {current_latest}")

    if latest_snapshot_block != current_latest:
        latest_snapshot_block = current_latest
        snapshots_done_after_restart += 1
        snapshots_count += 1

    print(f"Snapshots done after restart: {snapshots_done_after_restart}")

    if snapshots_count > 11:
        break

    time.sleep(0.6)

print("Exiting")

ch.stop()
