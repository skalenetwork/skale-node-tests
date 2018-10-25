from sktest import *
from sktest_helpers import *
import time
import json

ch = createDefaultChain(numNodes=2, numAccounts=2)
ch.start()

input("press enter")

ch.transactionAsync(nonce=0)
time.sleep(0.2)
ch.transactionAsync(nonce=1)
ch.transactionAsync(nonce=2)

print("State at node 1:")
print(dumpNodeState(ch.mainState()))
print("")
print("Diffs from state 1:")
print(dumpNodeState(ch.compareAllStates()))

#ch.stop()
print("Stopped")
