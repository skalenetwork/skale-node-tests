from sktest import *

import web3
from web3.auto import w3

w3.eth.enable_unaudited_features()

from hexbytes import HexBytes
 
global sktest_exe, sktest_proxy
#sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/scripts/aleth")
sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/build/Debug/skaled/skaled")
sktest_proxy = os.getenv("SKTEST_PROXY", "/home/dimalit/skale-ethereum/scripts/jsonrpcproxy.py")

class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)


def dump_node_state(obj):
    return json.dumps(obj, indent=1, cls=HexJsonEncoder)


def create_default_chain(num_nodes=2, num_accounts=2):
    nodes = []
    balances = []

    for i in range(num_nodes):
        nodes.append(Node())

    for i in range(num_accounts):
        balances.append(str((i + 1) * 1000000000))

    global sktest_exe, sktest_proxy
    starter = LocalStarter(sktest_exe, sktest_proxy)
    chain = SChain(nodes, starter, balances)
    return chain

def load_private_keys(path, password, count=0):
    #TODO Exceptions?!
    files = os.listdir(path)
    res = []
    i = 0
    for f in files:
        fd = open(path+"/"+f)
        key_crypted = fd.read()
        fd.close()
        key_open = w3.eth.account.decrypt(key_crypted, password)
        res.append(key_open)
        i += 1
        if count != 0 and i == count:
            break
    return res
