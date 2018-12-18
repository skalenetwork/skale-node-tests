from sktest_helpers import *
import time 
import threading

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

def send_func(eth, arr, begin, count):
    for i in range(begin, begin+count):
        t = arr[i]
        eth.sendRawTransaction(t)

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc)

ch.start()

input("press")

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

#for i in range(len(transactions)):
#    if i%10 == 0:
#        print("Sending %d" % i)
#    t = transactions[i]
#    ch.eth.sendRawTransaction(t)

for t in range(1):
    thread = threading.Thread(target=send_func, args=(ch.eth, transactions, t*1000, 1000))
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

