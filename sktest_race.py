from sktest_helpers import *
import time

ch = create_default_chain(num_nodes=2, num_accounts=2)
ch.start()

node1 = ch.nodes[0]
node2 = ch.nodes[1]
eth1  = node1.eth
eth2  = node2.eth

#NOTICE: consensus is won by 2-nd node at block #1 (after that - randomly)

eth2.pauseBroadcast(True)
eth2.pauseConsensus(True)

tx1 = ch.transaction_obj(_from=0, nonce=0)
tx2 = ch.transaction_obj(_from=1, nonce=0)

###############################################################################

# send tx on 1 - should be no blocks
eth2.sendRawTransaction(tx1)
eth1.forceBlock()

time.sleep(2)
assert(eth1.blockNumber == 0)
assert(eth2.blockNumber == 0)

# now should have txn
eth2.pauseConsensus(False)

time.sleep(2)
assert(eth1.blockNumber == 1)
assert(eth2.blockNumber == 1)
assert(count_txns(eth1)==1)
assert(count_txns(eth2)==1)

############################################

difference = ch.compare_all_states()

if difference is None:
    print('States on all nodes are consistent')
    print('*** Test passed ***')
else:
    print("Diffs from state 1:")
    print(dump_node_state(difference))
    print_states_difference(ch)
    print('*** Test failed ***')

#ch.stop()

