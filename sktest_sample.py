from sktest import *
from sktest_helpers import *
import time
import json
from hexbytes import HexBytes

class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)
cfg=Config()

n1=Node()
n2=Node()

starter = LocalStarter(sktest_exe, sktest_proxy)
chain = SChain([n1,n2], starter, ["123000000000", "4000000000"])

chain.start()

chain.transaction()
chain.transaction()

print("State at node 1:")
print(json.dumps(chain.mainState(), indent=1, cls=HexJsonEncoder))
print("")
print("Diffs from state 1:")
print(json.dumps(chain.compareAllStates(), indent=1, cls=HexJsonEncoder))

chain.stop()
print("Stopped")

