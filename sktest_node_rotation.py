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
snapshotIntervalMs = 5

run_container = os.getenv('RUN_CONTAINER')

n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalMs)
n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalMs)
n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalMs)
n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
          snapshotInterval=snapshotIntervalMs)
starter = LocalStarter(sktest_exe)


ch = SChain(
    [n1, n2, n3, n4],
    starter,
    prefill=[1000000000000000000, 2000000000000000000],
    emptyBlockIntervalMs=emptyBlockIntervalMs,
    snapshotIntervalMs=snapshotIntervalMs
)
ch.start(start_timeout=0)

# while True:
for _ in range(50):
    try:
        bn1 = n1.eth.blockNumber
        bn2 = n2.eth.blockNumber
        bn3 = n3.eth.blockNumber
        bn4 = n4.eth.blockNumber
        print(f"blockNumber's: {bn1} {bn2} {bn3} {bn4}")
    except:
        pass

    time.sleep(0.6)

print("Exiting")

ch.stop()
