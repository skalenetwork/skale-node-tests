from sktest_helpers import *
import time
import sys

nNodes = int(os.getenv("NUM_NODES", 4))
nTxns = 24000
nBlocks = 10000000000
if len(sys.argv) > 1:
    nBlocks = int(sys.argv[1])
nAcc  = 240

ch = create_custom_chain(num_nodes=nNodes, num_accounts=nAcc, empty_blocks = True, rotate_after_block=10, config_file="/home/dimalit/SkaleExperimental/skaled-tests/cat-cycle/init.json", chainID="0xD39D", bls=False)

ch.start()

print("Waiting for blocks")
pid = ch.nodes[0].pid
with open("/tmp/libleak.enabled", "w") as fp:
    fp.write(str(pid))

#time.sleep(60);
wait_for_blocks(ch, nBlocks)

with open("/tmp/libleak.enabled", "w") as fp:
    fp.write("")

#wait_for_txns(ch, nTxns)

#print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")

#input("Press enter")

ch.stop()
