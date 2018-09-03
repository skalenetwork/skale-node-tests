from sktest import *
from sktest import _node2json
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
n3=Node()

starter = LocalStarter("/home/dimalit/skale-ethereum/build/Debug/aleth/aleth", "/home/dimalit/skale-ethereum/scripts/jsonrpcproxy.py")
chain = SChain([n1,n2,n3], starter, ["123000000000", "4000000000"])
chain.start()
print("Started")

chain.block()
chain.transaction()

print(json.dumps(chain.compareAll(), indent=1, cls=HexJsonEncoder))
#print(json.dumps(info, indent=1, cls=HexJsonEncoder))

chain.stop()
print("Stopped")
