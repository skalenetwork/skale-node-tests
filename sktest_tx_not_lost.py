from sktest_helpers import *
import time

nTxns = 20
nWait = 20

ch = create_default_chain(num_nodes=2, num_accounts=2)
ch.start()

node1 = ch.nodes[0]
node2 = ch.nodes[1]
eth1  = node1.eth
eth2  = node2.eth

def wait_block_with_txns(eth):
    b1 = eth.blockNumber
    while eth.blockNumber==b1 or len(eth.getBlock("latest").transactions) == 0:
        time.sleep(0.1)
        if eth.blockNumber == b1 + nWait:
            print("Failed waiting for mined transaction for %d blocks" % nWait)
            ch.stop()
            exit()

eth1.pauseBroadcast(True)
sum1 = 0
sum2 = 0

for i in range(nTxns):
    tx = ch.transaction_obj(value=1, _from=0, to=1, nonce=i)
    print("Sending %d" % i)
    eth1.sendRawTransaction(tx)

    wait_block_with_txns(eth1)

    blk = eth1.blockNumber
    assert(eth2.blockNumber==blk)
    len1 = len(eth1.getBlock(blk).transactions)
    len2 = len(eth2.getBlock(blk).transactions)
    print("block %d at nodes has (%d, %d)" % (blk, len1, len2))
    sum1 += len1
    sum2 += len2

assert(eth2.blockNumber==eth1.blockNumber)
assert(sum1 == sum2)

ch.stop()

