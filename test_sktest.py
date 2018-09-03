from sktest import *
import time

cfg=Config()

n1=Node()
n2=Node()
n3=Node()

starter = LocalStarter("/home/dimalit/skale-ethereum/build/Debug/aleth/aleth", "/home/dimalit/skale-ethereum/scripts/jsonrpcproxy.py")
chain = SChain([n1,n2,n3], starter, ["123000000000", "4000000000"])
chain.start()
print("Started")

print(chain.balance(0))
#input("press enter")

print(chain.transaction(value=0))
print(chain.balance(0))

input("press enter")
chain.stop()
print("Stopped")
