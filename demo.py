from sktest import *
config = Config()
config = Config({"genesis.gasLimit": "0x47E7C5"})
n1 = Node()
n2 = Node()
n3 = Node()
starter = LocalStarter("/home/dimalit/skale-ethereum/scripts/aleth", "/home/dimalit/skale-ethereum/scripts/jsonrpcproxy.py")
chain = SChain([n1, n2, n3], starter, [10000000000, 5000000000, 1000000000], config)
chain.start()

