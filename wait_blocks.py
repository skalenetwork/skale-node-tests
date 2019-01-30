from sktest_helpers import *
import time 

nNodes = int(os.getenv("NUM_NODES", 4))
nTxns = 24000
nAcc  = 24000

def count_txns(ch):
    sum = 0
    for i in range(ch.eth.blockNumber+1):
        b = ch.eth.getBlock(i)
        n = len(b.transactions)
        sum += n
    return sum

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc)

ch.start()

print("Waiting for blocks")
t1 = time.time()
count = 0

while count != nTxns:
    count = count_txns(ch)

    t2 = time.time()

    if t2!=t1:
        print("%d txns %d blocks perf = %f tx/sec" % (count, ch.eth.blockNumber, count/(t2-t1)))
    
    time.sleep(0.5)

t2 = time.time()

print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")
ch.stop()
