from sktest import *

n1 = Node(bindIP="192.168.0.100")
n2 = Node(bindIP="192.168.0.110")

ssh_config = [
    {"address": "dimalit@dimalit-pc.local", "dir": "/home/dimalit/skale-node-tests/tmp", "exe": "/home/dimalit/skale-ethereum/build/Debug/skaled/skaled"},
    {"address": "stan@stan-pc.local", "dir": "/home/stan/skaled", "exe": "/home/stan/skaled/skaled"}
]

starter = RemoteStarter(ssh_config)
ch = SChain([n1, n2], starter, prefill=[1000000000000000000, 2000000000000000000])

ch.start()

input("press enter")

assert (ch.eth.blockNumber == 0)
assert (ch.nonce(0) == 0)

balance = ch.balance(0)
ch.transaction()

assert (ch.eth.blockNumber == 1)
assert (ch.nonce(0) == 1)
assert (balance > ch.balance(0))

ch.stop()

