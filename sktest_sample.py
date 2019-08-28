from sktest import *
from sktest_helpers import *
import time
import json

num_nodes=int(os.getenv("NUM_NODES", 4))
ch = create_default_chain(num_nodes=num_nodes, num_accounts=2)
ch.start()

# input("press enter")

ch.transaction()
ch.transaction()

# print("State at node 1:")
# print(dump_node_state(ch.main_state()))
# print("")

difference = None
if num_nodes > 1:
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
#print("Stopped")
