from sktest import *
import os

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

global sktest_exe
sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skaled/build-no-mp/skaled/skaled")

emptyBlockIntervalMs = 2000
snapshotIntervalMs = 10

n1 = Node()
n2 = Node()
n3 = Node()
n4 = Node(snapshottedStartSeconds=140) #90 #18

starter = LocalStarter(sktest_exe)
ch = SChain([n1, n2, n3, n4], starter, prefill=[1000000000000000000, 2000000000000000000], emptyBlockIntervalMs=emptyBlockIntervalMs, snapshotIntervalMs=snapshotIntervalMs)
ch.start(start_timeout = 0) # 300

print("Waiting for full catch-up")

while True:
    bn1 = n1.eth.blockNumber
    bn2 = n2.eth.blockNumber
    bn3 = n3.eth.blockNumber
    
    try:
        bn4 = n4.eth.blockNumber
    except:
        bn4 = None

    print(f"blockNumber's: {bn1} {bn2} {bn3} {bn4}")

    if bn1==bn2 and bn2==bn3 and bn3==bn4:
        break

    time.sleep(0.6)

print("Exiting")

ch.stop()
