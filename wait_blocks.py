from sktest_helpers import *
import time

nNodes = int(os.getenv("NUM_NODES", 4))
nTxns = 24000
nAcc  = 24000

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc)

ch.start()

print("Waiting for blocks")

wait_for_txns(ch, nTxns)

#print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")
ch.stop()
