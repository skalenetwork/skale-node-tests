from sktest_helpers import *
import time
import threading

nNodes = int(os.getenv("NUM_NODES", 16))
nTxns = 100#24000
nAcc  = 100#8000
nThreads = 1

def send_func(eth, arr, begin, count):
    for i in range(begin, begin+count):
        while(True):
            try:
                t = arr[i]
                eth.sendRawTransaction(t)
                break
            except Exception as e:
                print(e)
                time.sleep(0.1)

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc)

ch.start()

transactions = generate_or_load_txns(ch, nAcc, nTxns)

#print("Sleeping 15 sec")
#time.sleep(15)

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

dt = wait_for_txns(ch, nTxns)

print("Txns: "+str(nTxns)+" Time: "+str(dt)+" => "+str(nTxns/(dt))+" tx/sec")

ok = True
for i in range(nNodes):
    ntx = count_txns(ch.nodes[i].eth)
    print("Node%d: %d txns" % (i, ntx))
    if ntx != nTxns:
        ok = False

if ok:
    print('*** Test passed ***')
else:
    print('*** Test failed ***')

# input("press enter")
#
# time.sleep(3)
# difference = ch.compare_all_states()
#
# if difference is None:
#     print('States on all nodes are consistent')
#     print('*** Test passed ***')
# else:
#     print("Diffs from state 1:")
#     print(dump_node_state(difference))
#     states = [ch.state(index) for index in range(nNodes)]
#     for a_index in range(nNodes):
#         for b_index in range(a_index + 1, nNodes):
#             diff = list_differences(states[a_index], states[b_index])
#             if diff:
#                 print('')
#                 print(f'Difference between node #{a_index + 1} and #{b_index + 1}')
#                 print('\n'.join(diff))
#     print('*** Test failed ***')

#ch.stop()

