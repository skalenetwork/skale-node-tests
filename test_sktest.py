from sktest import *

cfg=Config()

n1=Node()
n2=Node()

chain = SChain([n1,n2])
starter = LocalStarter(chain, "/home/dimalit/skale-ethereum/build/Debug/aleth/aleth", "pofig")
