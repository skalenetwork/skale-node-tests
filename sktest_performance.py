from sktest_helpers import *
import time 

nNodes = 1
nTxns = 1000
nAcc  = 1000

def have_all(ch):
    sum = 0
    for i in range(ch.eth.blockNumber+1):
        b = ch.eth.getBlock(i)
        n = len(b.transactions)
        sum += n
    print("txns: %d blocks: %d" % (sum, ch.eth.blockNumber))
    return sum == nTxns

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc)

ch.start()
input("press")

filter = ch.all_filter('latest')

t1 = time.time()

for i in range(nTxns):
    acc1 = i % nAcc
    acc2 = (i+1) % nAcc
    nonce = i // nAcc
    print("from=%d nonce=%d %s" % (acc1, nonce, ch.accounts[acc1]))
    ch.transaction_async(value=1, _from=acc1, to=acc2, nonce=nonce)

print("Waiting for blocks")
while not have_all(ch):
    ch.wait_all_filter(filter)

t2 = time.time()

print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")

#print(dump_node_state(ch.compare_all_states()))
ch.stop()

