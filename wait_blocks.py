from sktest_helpers import *
import time

nNodes = int(os.getenv("NUM_NODES", 4))
nTxns = 240000
nBlocks = 10000
nAcc  = 240

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc, config_file="/home/dimalit/SkaleExperimental/skaled-tests/cat-cycle/init.json")

ch.start()

print("Waiting for blocks")

wait_for_txns(ch, nTxns)
#wait_for_blocks(ch, nBlocks)

#print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")
ch.stop()
