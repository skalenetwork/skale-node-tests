from sktest import Node, SChain, Config

nodes = [Node(bindIP="127.0.0.2"), Node(), Node(nodeName="nn")]
config = Config()
config.networkID = '2121'
config.accounts.append({'0xabcdef1234567890':{'balance':'10000000000000000'}})

chain = SChain(nodes, prefill = ['1000000000', '100000000000000'], config=config)
chain.start()

print chain.running()
print chain.nodes[0].eth.getBalance(chain.accounts[0])
chain.transaction(0, 1, 1000000)
nodes[0].eth.....

chain.stop()


