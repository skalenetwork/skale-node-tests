from sktest import *

from hexbytes import HexBytes
 
global sktest_exe, sktest_proxy
#sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/scripts/aleth")
sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/build/Debug/aleth/aleth")
sktest_proxy = os.getenv("SKTEST_PROXY", "/home/dimalit/skale-ethereum/scripts/jsonrpcproxy.py")

class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)

def dumpNodeState(obj):
    return json.dumps(obj, indent=1, cls=HexJsonEncoder)

def createDefaultChain(numNodes=2, numAccounts=2):
    cfg=Config()
    nodes = []
    balances = []

    for i in range(numNodes):
        nodes.append(Node())
    
    balance = 128000000000
    for i in range(numAccounts):
        balances.append(str((i+1)*1000000000))

    global sktest_exe, sktest_proxy
    starter = LocalStarter(sktest_exe, sktest_proxy)
    chain = SChain(nodes, starter, balances)
    return chain

