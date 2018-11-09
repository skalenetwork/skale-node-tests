from sktest_helpers import *
import time 

nNodes = 1
nTxns = 1000
nAcc  = 1000

def count_txns(ch):
    sum = 0
    for i in range(ch.eth.blockNumber+1):
        b = ch.eth.getBlock(i)
        n = len(b.transactions)
        sum += n
    return sum

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc)

ch.start()
input("press")

#filter = ch.all_filter('latest')
transactions = []

print("Generating txns")
for i in range(nTxns):
    acc1 = i % nAcc
    acc2 = (i+1) % nAcc
    nonce = i // nAcc
    print("from=%d nonce=%d %s" % (acc1, nonce, ch.accounts[acc1]))
    transactions.append( ch.transaction_obj(value=1, _from=acc1, to=acc2, nonce=nonce) )

print("Sending txns")
t1 = time.time()

for i in range(len(transactions)):
    print("Sending %d" % i)
    t = transactions[i]
    ch.eth.sendRawTransaction(t)

print("Waiting for blocks")
count = 0
while count != nTxns:
    count = count_txns(ch)
    t2 = time.time()
    print("%d txns %d blocks perf = %f tx/sec" % (count, ch.eth.blockNumber, count/(t2-t1)))
    time.sleep(0.5)

t2 = time.time()

print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")

#print(dump_node_state(ch.compare_all_states()))
ch.stop()

