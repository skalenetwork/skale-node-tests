from sktest_helpers import *
import time

nAcc = 10
nTxns = 30

# node = Node()
# print(node.__dict__)
# balances = []

# for i in range(nAcc):
#     balances.append(str((i+1)*1000000000))
# starter = NoStarter()
# ch = SChain([node], starter, balances)

ch = create_default_chain(num_nodes=3, num_accounts=nAcc)

ch.start()
input("press")

t1 = time.time()

for i in range(nTxns):

    acc1 = i % nAcc
    acc2 = (i+1) % nAcc
    nonce = i//nAcc

    while True:
        try:
            time.sleep(0.2)
            print("from=%d nonce=%d" % (acc1, nonce))
            ch.transaction_async(value=1, _from=acc1, to=acc2, nonce=nonce)
            break
        except ValueError as e:
            if not hasattr(e, 'args') or e.args[0]['message'] != 'Invalid transaction nonce.':
                raise

t2 = time.time()

time.sleep(4)
print(dump_node_state(ch.compare_all_states()))
ch.stop()
print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")
