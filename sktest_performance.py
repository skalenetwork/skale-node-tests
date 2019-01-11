from sktest_helpers import *
import time
import threading

nNodes = 4
nTxns = 24000
nAcc  = 24000
nThreads = 1

def count_txns(ch):
    sum = 0
    for i in range(ch.eth.blockNumber+1):
        b = ch.eth.getBlock(i)
        n = len(b.transactions)
        sum += n
    return sum

def send_func(eth, arr, begin, count):
    for i in range(begin, begin+count):
        t = arr[i]
        eth.sendRawTransaction(t)

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc)

ch.start()

input("press")

transactions = []

try:
    with open("transactions.all", "rb") as fd:
        transactions = pickle.load(fd)
    print("Loaded transactions from file")
except Exception as ex:
    print("Generating txns")
    for i in range(nTxns):
        acc1 = i % nAcc
        acc2 = (i+1) % nAcc
        nonce = i // nAcc
        print("from=%d nonce=%d %s" % (acc1, nonce, ch.accounts[acc1]))
        txn_str = ch.transaction_obj(value=1, _from=acc1, to=acc2, nonce=nonce)
        transactions.append( txn_str )
    with open("transactions.all", "wb") as fd:
        pickle.dump(transactions, fd)

#print("Sleeping 15 sec")
#time.sleep(15)

input("Sending txns - press")
t1 = time.time()

#for i in range(len(transactions)):
#    if i%10 == 0:
#        print("Sending %d" % i)
#    t = transactions[i]
#    ch.eth.sendRawTransaction(t)

txns_per_thread = nTxns // nThreads

assert txns_per_thread*nThreads == nTxns

for t in range(nThreads):
    n = ch.nodes[0]
    eth = web3.Web3(web3.Web3.HTTPProvider("http://" + n.bindIP + ":" + str(n.basePort + 3))).eth
    #eth = web3.Web3(web3.Web3.IPCProvider(n.ipcPath)).eth
    thread = threading.Thread(target=send_func, args=(eth, transactions, t*txns_per_thread, txns_per_thread))
    thread.start()

print("Waiting for blocks")
count = 0
while count != nTxns:
    count = count_txns(ch)
    t2 = time.time()
    print("%d txns %d blocks perf = %f tx/sec" % (count, ch.eth.blockNumber, count/(t2-t1)))
    time.sleep(0.5)

t2 = time.time()

print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")

input("press enter")

time.sleep(3)
difference = ch.compare_all_states()

if difference is None:
    print('States on all nodes are consistent')
    print('*** Test passed ***')
else:
    print("Diffs from state 1:")
    print(dump_node_state(difference))
    states = [ch.state(index) for index in range(nNodes)]
    for a_index in range(nNodes):
        for b_index in range(a_index + 1, nNodes):
            diff = list_differences(states[a_index], states[b_index])
            if diff:
                print('')
                print(f'Difference between node #{a_index + 1} and #{b_index + 1}')
                print('\n'.join(diff))
    print('*** Test failed ***')

ch.stop()

