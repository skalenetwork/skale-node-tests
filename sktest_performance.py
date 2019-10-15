from sktest_helpers import *
import time
import threading
from functools import reduce

nNodes = int(os.getenv("NUM_NODES", 4))
nTxns = 24000 #24000
nAcc  = 240 #8000
nThreads = 0

MAX_RETRIES = 30

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

def compare_nodes(nodes):
    bn1 = 0
    bn2 = 0

    try:
        bn1 = nodes[0].eth.blockNumber
    except:
        pass
    try:
        bn2 = nodes[1].eth.blockNumber
    except:
        pass
    
    bn = max(bn1, bn2)
    
    b = 0
    while b <= bn:
        line = ""
        arr = []
        for n in nodes:
            try:
                val = len(n.eth.getBlock(b).transactions)
                line += str(val) + " "
                arr.append(val)
            except Exception as ex:
                b -= 1
                time.sleep(1)
                break
    
        equal = True
        if len(arr)==len(nodes):
            equal = all(arr[0]==e for e in arr)

        if not equal:
            print(f"\nblock {b}: {line}")
        else:
            print('.', end='')
        b += 1

ch = create_default_chain(num_nodes=nNodes, num_accounts=nAcc, empty_blocks = True)

ch.start(start_timeout = 10)

transactions = generate_or_load_txns(ch, nAcc, nTxns)

t1 = time.time()

if nThreads == 0:
    i = 0
    while i < len(transactions):

        t = transactions[i]
        retries = 0
        while True:
            try:
                hash = ch.nodes[0].eth.sendRawTransaction(t)
                print(i, "0x" + binascii.hexlify(hash).decode("utf-8"))
                break
            except Exception as e:
#                print(e)
                try:
                    hash = ch.nodes[1].eth.sendRawTransaction(t)
                    print(i, "0x" + binascii.hexlify(hash).decode("utf-8") + " (2)")
                    break
                except Exception as e2:
                    print(e2)
                    retries += 1
                    if retries == MAX_RETRIES:
                        os.system("pkill -9 -f kill4")
                        compare_nodes(ch.nodes)
                        raw_prev = None
                        if i-nAcc >= 0:
                            raw_prev = transactions[i-nAcc] 
                        print(f"i={i} offending tx is {t}")
                        print(f"prev tx i={i-nAcc} is {raw_prev}")
                        exit()
#                    	i -= nAcc			# repeat previous nonce!
#                    	i = max(i, 0)
#                    	print(f"Stepping back to {i}")
                    time.sleep(1)
        i += 1
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

dt = wait_for_txns(ch, nTxns-1)

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

