from sktest import *
from sktest_helpers import *
import time
import traceback

nAcc = 10

#node = Node()
#print(node.__dict__)
#balances = []

#for i in range(nAcc):
#    balances.append(str((i+1)*1000000000))
#starter = NoStarter()
#ch = SChain([node], starter, balances)

ch = createDefaultChain(numNodes=3, numAccounts=nAcc)

ch.start()
input("press")

for i in range(30):

    acc1 = i % nAcc
    acc2 = (i+1) % nAcc
    nonce = i//nAcc

    while True:
        try:
            time.sleep(0.2)
            print("from=%d nonce=%d" % (acc1, nonce))
            ch.transactionAsync(value=1, _from=acc1, to=acc2, nonce=nonce)
            break
        except ValueError as e:
            if not hasattr(e, 'args') or e.args[0]['message']!='Invalid transaction nonce.':
                raise

time.sleep(4)
print(dumpNodeState(ch.compareAllStates()))
ch.stop()

