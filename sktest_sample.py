from sktest import *
from sktest_helpers import *
import time
import json

ch = createDefaultChain(numNodes=2, numAccounts=2)
ch.start()

input("press enter")

ch.transaction()
#ch.transaction()

print("State at node 1:")
print(dumpNodeState(ch.mainState()))
print("")
print("Diffs from state 1:")
print(dumpNodeState(ch.compareAllStates()))

ch.stop()
print("Stopped")

