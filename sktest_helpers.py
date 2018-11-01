from sktest import *

from hexbytes import HexBytes

# sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/scripts/aleth")
sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/build/Debug/aleth/aleth")
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
