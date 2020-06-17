import os

from sktest_helpers import create_default_chain, dump_node_state, \
    print_states_difference

num_nodes = int(os.getenv("NUM_NODES", 2))
ch = create_default_chain(num_nodes=num_nodes, num_accounts=2,
                          empty_blocks=True)
ch.start()

# input("press enter")

ch.transaction()
ch.transaction()

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
