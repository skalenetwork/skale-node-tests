import os
import time
from sktest import LocalStarter, Node, SChain

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

global sktest_exe
sktest_exe = os.getenv("SKTEST_EXE",
                       "/home/dimalit/skaled/build-no-mp/skaled/skaled")

emptyBlockIntervalMs = 1
snapshotIntervalSec = 10

run_container = os.getenv('RUN_CONTAINER')

n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec)
n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec)
n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec)
n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalSec,
          snapshottedStartSeconds=90)  # 90 # 18
starter = LocalStarter(sktest_exe)

ch = SChain(
    [n1, n2, n3, n4],
    starter,
    prefill=[1000000000000000000, 2000000000000000000],
    emptyBlockIntervalMs=emptyBlockIntervalMs,
    snapshotIntervalSec=snapshotIntervalSec,
    bls=True
)
ch.start(start_timeout=300, restart_option=True)  # 300

print("Waiting for full catch-up")

# while True:
for _ in range(50):
    bn1 = n1.eth.blockNumber
    bn2 = n2.eth.blockNumber
    bn3 = n3.eth.blockNumber

    try:
        bn4 = n4.eth.blockNumber
    except Exception:
        bn4 = None

    print(f"blockNumber's: {bn1} {bn2} {bn3} {bn4}")

    if bn1 == bn2 and bn2 == bn3 and bn3 == bn4:
        break

    try:
        ch.transaction_async()
    except:
        pass    # already exists

    time.sleep(0.6)

print("Exiting")

ch.stop()
