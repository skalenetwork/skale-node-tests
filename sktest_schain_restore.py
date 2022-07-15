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

n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec, bls=True)
n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec, bls=True)
n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec, bls=True)
n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec, bls=True)
starter = LocalStarter(sktest_exe)


ch = SChain(
    [n1, n2, n3, n4],
    starter,
    prefill=[1000000000000000000, 2000000000000000000],
    emptyBlockIntervalMs=emptyBlockIntervalMs,
    snapshotIntervalSec=snapshotIntervalSec
)
ch.start(start_timeout=90)

while True:
    latest_snapshot_n1 = n1.eth.getLatestSnapshotBlockNumber()
    latest_snapshot_n2 = n2.eth.getLatestSnapshotBlockNumber()
    latest_snapshot_n3 = n3.eth.getLatestSnapshotBlockNumber()
    latest_snapshot_n4 = n4.eth.getLatestSnapshotBlockNumber()

    if latest_snapshot_n1 == latest_snapshot_n2 and latest_snapshot_n1 == latest_snapshot_n3 and latest_snapshot_n1 == latest_snapshot_n4 and latest_snapshot_n1 >= 15:
        print("Exiting")
        ch.stop_without_cleanup()
        break
    
    sleep(1)

print(f"Delete all snapshots except {latest_snapshot_n1}")
ch.prepare_to_restore(latest_snapshot_n1)

print("Restarting skaled")

ch.start_after_stop(start_timeout=120)

while True:
    bn1 = n1.eth.blockNumber
    bn2 = n2.eth.blockNumber
    bn3 = n3.eth.blockNumber
    bn4 = n4.eth.blockNumber
    
    if bn1 == bn2 and bn2 == bn3 and bn3 == bn4 and bn4 >= 50:
        break

    sleep(0.6)

print("Exiting")
ch.stop_without_cleanup()
