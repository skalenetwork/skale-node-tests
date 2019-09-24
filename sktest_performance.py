from sktest_helpers import *
import time
import threading

nNodes = int(os.getenv("NUM_NODES", 4))
nTxns = 4000 #24000
nAcc  = 1000 #8000
nThreads = 0

def send_func(eth, arr, begin, count):
    for i in range(begin, begin+count):
        while(True):
            try:
                t = arr[i]
                eth.sendRawTransaction(t)
                break
            except Exception as e:
                print(e)
                time.sleep(1)

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc, empty_blocks = True)

ch.start(start_timeout = 0)

transactions = generate_or_load_txns(ch, nAcc, nTxns)

t1 = time.time()

if nThreads == 0:
    for i in range(len(transactions)):

        if i % 100 == 0:
            print(str(i))

        t = transactions[i]
        while True:
            try:
                hash = ch.nodes[0].eth.sendRawTransaction(t)
                print(i, "0x" + binascii.hexlify(hash).decode("utf-8"))
                break
            except Exception as e:
                print(e)
                try:
                    hash = ch.nodes[1].eth.sendRawTransaction(t)
                    print(i, "0x" + binascii.hexlify(hash).decode("utf-8"))
                    break
                except Exception as e2:
                    print(e2)
                    time.sleep(1)
else:
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

#ch.stop()

