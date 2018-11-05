from sktest_helpers import *
import time 

nNodes = 3
nTxns = 1000

ch = create_default_chain(num_nodes=nNodes, num_accounts=2)

ch.start()
input("press")

t1 = time.time()

for i in range(nTxns):
    print("from=%d nonce=%d" % (1, i))
    ch.transaction_async(value=1, _from=1, to=0, nonce=i)

t2 = time.time()

time.sleep(4)
print(dump_node_state(ch.compare_all_states()))
ch.stop()
print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")
