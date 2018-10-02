from sktest import *
from sktest_helpers import *
import time
import json

cfg=Config()

n1=Node()
n2=Node()

starter = LocalStarter(sktest_exe, sktest_proxy)
chain = SChain([n1,n2], starter, ["123000000000", "4000000000"])

chain.start()

input("press enter")

chain.transaction()
chain.transaction()

print("State at node 1:")
print(dumpNodeState(chain.mainState()))
print("")
print("Diffs from state 1:")
print(dumpNodeState(chain.compareAllStates()))

chain.stop()
print("Stopped")

