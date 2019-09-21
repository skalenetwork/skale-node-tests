from sktest import *
import os

global sktest_exe
sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skaled/build-no-mp/skaled/skaled")

emptyBlockIntervalMs = 10000
snapshotInterval = 10

n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs, snapshotInterval=snapshotInterval)
n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs, snapshotInterval=snapshotInterval)
n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs, snapshotInterval=snapshotInterval)
n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs, snapshotInterval=snapshotInterval, snapshottedStartSeconds=111)

starter = LocalStarter(sktest_exe)
ch = SChain([n1, n2, n3, n4], starter, prefill=[1000000000000000000, 2000000000000000000])
ch.start()


ch.stop()

