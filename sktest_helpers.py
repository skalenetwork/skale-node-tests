from sktest import *
 
global sktest_exe, sktest_proxy
sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/scripts/aleth")
sktest_proxy = os.getenv("SKTEST_PROXY", "/home/dimalit/skale-ethereum/scripts/jsonrpcproxy.py")

def createDefaultChain(numNodes=2, numAccounts=2):
    cfg=Config()
    nodes = []
    balances = []

    for i in range(numNodes):
        nodes.append(Node())
    
    balance = 128000000000
    for i in range(numAccounts):
        balances.append(str(balance))
        balance //= 2

    global sktest_exe, sktest_proxy
    starter = LocalStarter(sktest_exe, sktest_proxy)
    chain = SChain(nodes, starter, balances)
    return chain

