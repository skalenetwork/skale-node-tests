import os
import time
from sktest import LocalStarter, LocalDockerStarter, Node, SChain

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

global sktest_exe
sktest_exe = os.getenv("SKTEST_EXE",
                       "/home/dimalit/skaled/build-no-mp/skaled/skaled")

emptyBlockIntervalMs = 2000
snapshotIntervalMs = 6000

run_container = os.getenv('RUN_CONTAINER')

if run_container is not None:
    node = Node(bindIP='127.0.0.1', basePort=10000,
              emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalMs)
    starter = LocalDockerStarter()
else:
    node = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalMs)
    starter = LocalStarter(sktest_exe)


ch = SChain(
    [node],
    starter,
    prefill=[1000000000000000000, 2000000000000000000],
    emptyBlockIntervalMs=emptyBlockIntervalMs,
    snapshotIntervalMs=snapshotIntervalMs
)
ch.start(start_timeout=0)

print("Waiting for snapshots to be done")

snapshots_count = 0
latest_snapshot_block = 0

while True:
    bn = node.eth.blockNumber

    print(f"blockNumber is: {bn}")

    current_latest = getLatestSnapshotBlockNumber(node.eth)
    if latest_snapshot_block != current_latest:
        latest_snapshot_block = current_latest
        snapshots_count += 1

    print(f"Snapshots done: {snapshots_count}")

    if snapshots_count > 5:
        break

    time.sleep(0.6)

ch.stop()

print("Restarting skaled")

ch.start(start_timeout=0)

print("Waiting for snapshots to be done after restart")

while True:
    bn = node.eth.blockNumber

    print(f"blockNumber is: {bn}")

    print(f"Snapshots done after restart: {snapshots_count}")

    if snapshots_count > 11:
        break

    time.sleep(0.6)

print("Exiting")

ch.stop()