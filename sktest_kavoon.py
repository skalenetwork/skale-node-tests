from sktest_helpers import *
import time

num_nodes = 2
ch = create_default_chain(num_nodes, num_accounts=4)
ch.start()

node1 = ch.nodes[0]
node2 = ch.nodes[1]
eth1  = node1.eth
eth2  = node2.eth

eth1.pauseBroadcast(True)
eth2.pauseBroadcast(True)

tx1 = ch.transaction_obj(_from=0, nonce=0)
tx2 = ch.transaction_obj(_from=1, nonce=0)
tx3 = ch.transaction_obj(_from=2, nonce=0)
tx4 = ch.transaction_obj(_from=3, nonce=0)


eth2.sendRawTransaction(tx1)
time.sleep(1)
eth1.sendRawTransaction(tx1)
ch.wait_block()

eth2.sendRawTransaction(tx2)
time.sleep(1)
eth1.sendRawTransaction(tx2)
ch.wait_block()

eth2.sendRawTransaction(tx3)
time.sleep(1)
eth1.sendRawTransaction(tx3)
ch.wait_block()

time.sleep(2)

############################################

difference = difference = ch.compare_all_states()

if difference is None:
    print('States on all nodes are consistent')
    print('*** Test passed ***')
else:
    states = [ch.state(index) for index in range(num_nodes)]
    for a_index in range(num_nodes):
        for b_index in range(a_index + 1, num_nodes):
            diff = list_differences(states[a_index], states[b_index])
            if diff:
                print('')
                print(f'Difference between node #{a_index + 1} and #{b_index + 1}')
                print('\n'.join(diff))
    print('*** Test failed ***')

input("press")
ch.stop()

