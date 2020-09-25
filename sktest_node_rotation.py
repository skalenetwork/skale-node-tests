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
snapshotIntervalMs = 1

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

while True:
#for _ in range(50):
    try:
        bn1 = n1.eth.blockNumber
        bn2 = n2.eth.blockNumber
        bn3 = n3.eth.blockNumber
        bn4 = n4.eth.blockNumber
        print(f"blockNumber's: {bn1} {bn2} {bn3} {bn4}")
        
        if bn1 == 5:
            args = ['--public-key', '18219295635707015937645445755505569836731605273220943516712644721479866137366:13229549502897098194754835600024217501928881864881229779950780865566962175067:3647833147657958185393020912446135601933571182900304549078758701875919023122:2426298721305518429857989502764051546820660937538732738470128444404528302050']
            args.append("--download-snapshot")
            args.append("http://" + ch.nodes[0].bindIP + ":" + str(ch.nodes[0].basePort + 3))  # noqa
            starter.restart_node(3, args)

        if bn1 >= 10 and bn1==bn2 and bn2==bn3 and bn3==bn4:
            break

    except:
        pass

    time.sleep(0.6)

print("Exiting")

ch.stop()
