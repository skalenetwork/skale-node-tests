from sktest_helpers import *
import time

nAcc = 10
nTxns = 100
num_nodes = 2

# node = Node()
# print(node.__dict__)
# balances = []

# for i in range(nAcc):
#     balances.append(str((i+1)*1000000000))
# starter = NoStarter()
# ch = SChain([node], starter, balances)

ch = create_default_chain(num_nodes=num_nodes, num_accounts=nAcc)

ch.start()
# input("press enter")

start_nonce = {account: ch.nonce(account) for account in range(nAcc)}

start_balance = {account: ch.balance(account) for account in range(nAcc)}
print('Balances:', start_balance)

t1 = time.time()

for i in range(nTxns):

    acc1 = i % nAcc
    acc2 = (i+1) % nAcc
    nonce = start_nonce[acc1] + i // nAcc

    while True:
        try:
            while ch.nonce(acc1) < nonce:
                time.sleep(0.2)
            print(f"Send from account #{acc1} (nonce={nonce})")
            ch.transaction_async(value=1, _from=acc1, to=acc2, nonce=nonce)
            break
        except ValueError as e:
            if hasattr(e, 'args') and e.args[0]['message'] == 'Invalid transaction nonce.':
                current_nonce = ch.nonce(acc1)
                print(f"Nonce = {nonce} is invalid for account {acc1}. Current nonce is {current_nonce}.")
            else:
                raise e

            # if not hasattr(e, 'args') or e.args[0]['message'] != 'Invalid transaction nonce.':
            #     raise

t2 = time.time()

time.sleep(4)

print('Comparing final states...')
difference = ch.compare_all_states()

if difference is None:
    print('States on all nodes are consistent')
    print('*** Test passed ***')
else:
    # print("Diffs from state 1:")
    # print(dump_node_state(difference))

    states = [ch.state(index) for index in range(num_nodes)]
    for a_index in range(num_nodes):
        for b_index in range(a_index + 1, num_nodes):
            diff = list_differences(states[a_index], states[b_index])
            if diff:
                print('')
                print(f'Difference between node #{a_index + 1} and #{b_index + 1}')
                print('\n'.join(diff))
    print('*** Test failed ***')

ch.stop()
print("Txns: "+str(nTxns)+" Time: "+str(t2-t1)+" => "+str(nTxns/(t2-t1))+" tx/sec")
