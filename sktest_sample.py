from sktest import *
from sktest_helpers import *
import time
import json

num_nodes=int(os.getenv("NUM_NODES", 2))
ch = create_default_chain(num_nodes=2, num_accounts=2)
ch.start()

# input("press enter")

ch.nodes[0].eth.pauseConsensus(True)
ch.transaction_async(_from=0, nonce=0)
ch.transaction_async(_from=1, nonce=0)
ch.nodes[0].eth.pauseConsensus(False)

# print("State at node 1:")
# print(dump_node_state(ch.main_state()))
# print("")

print('Comparing')
difference = None
if num_nodes > 1:
    difference = ch.compare_all_states()

print('Printing result')
if difference is None:
    print('States on all nodes are consistent')
    print('*** Test passed ***')
else:
    print("Diffs from state 1:")
    print(dump_node_state(difference))
    print_states_difference(ch)
    print('*** Test failed ***')

print('Stopping')
ch.stop()
print("Stopped")
