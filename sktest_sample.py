from sktest import *
from sktest_helpers import *
import time
import json

ch = create_default_chain(num_nodes=2, num_accounts=2)
ch.start()

# input("press enter")

ch.transaction()
ch.transaction()

# print("State at node 1:")
# print(dump_node_state(ch.main_state()))
# print("")

difference = ch.compare_all_states()

if difference is None:
    print('States on all nodes are consistent')
    print('*** Test passed ***')
else:
    print("Diffs from state 1:")
    print(dump_node_state(difference))
    print('*** Test failed ***')

#ch.stop()
#print("Stopped")
