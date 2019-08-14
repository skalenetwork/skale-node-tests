from sktest import *

import web3
from web3.auto import w3

w3.eth.enable_unaudited_features()

from hexbytes import HexBytes
 
global sktest_exe
#sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/scripts/aleth")
sktest_exe = os.getenv("SKTEST_EXE", "/home/dimalit/skale-ethereum/build/Debug/skaled/skaled")

class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)


def dump_node_state(obj):
    return json.dumps(obj, indent=1, cls=HexJsonEncoder)


def create_default_chain(num_nodes=2, num_accounts=2):
    nodes = []
    balances = []

    for i in range(num_nodes):
        nodes.append(Node())

    for i in range(num_accounts):
        balances.append(str((i + 1) * 1000000000000000000000))

    global sktest_exe
    starter = LocalStarter(sktest_exe)
    chain = SChain(nodes, starter, balances)
    return chain

def load_private_keys(path, password, count=0):
    #TODO Exceptions?!
    files = os.listdir(path)
    res = []
    i = 0
    for f in files:
        fd = open(path+"/"+f)
        key_crypted = fd.read()
        fd.close()
        key_open = w3.eth.account.decrypt(key_crypted, password)
        res.append(key_open)
        i += 1
        if count != 0 and i == count:
            break
        if i % 10 == 0:
            print(f"Loaded {i} of {count} keys")
    return res

def count_txns(eth):
    sum = 0
    for i in range(eth.blockNumber+1):
        b = eth.getBlock(i)
        n = len(b.transactions)
        sum += n
    return sum

def generate_or_load_txns(ch, nAcc, nTxns):

    transactions = []
    file = "transactions_"+str(nAcc)+"_"+str(nTxns)

    try:
        with open(file, "rb") as fd:
            transactions = pickle.load(fd)
        print("Loaded transactions from file")
    except Exception as ex:
        print("Generating txns")
        for i in range(nTxns):
            acc1 = i % nAcc
            acc2 = (i+1) % nAcc
            nonce = i // nAcc
            print("from=%d nonce=%d %s" % (acc1, nonce, ch.accounts[acc1]))
            txn_str = ch.transaction_obj(value=1, _from=acc1, to=acc2, nonce=nonce)
            transactions.append( txn_str )
        safe_input_with_timeout("Sending txns - press", 10)
        with open(file, "wb") as fd:
            pickle.dump(transactions, fd)

    return transactions

def wait_for_txns(ch, nTxns):
    t1 = time.time()
    count = 0

    while count != nTxns:

        while True:
            try:
                count = count_txns(ch.eth)
                break
            except Exception as e:
                print(e)

        t2 = time.time()

        if t2!=t1:
            print("%d txns %d blocks perf = %f tx/sec" % (count, ch.eth.blockNumber, count/(t2-t1)))

        time.sleep(1)

    t2 = time.time()

    return t2-t1

def print_states_difference(ch):
    nNodes = len(ch.nodes)
    states = [ch.state(index) for index in range(nNodes)]
    for a_index in range(nNodes):
        for b_index in range(a_index + 1, nNodes):
            diff = list_differences(states[a_index], states[b_index])
            if diff:
                print('')
                print(f'Difference between node #{a_index + 1} and #{b_index + 1}')
                print('\n'.join(diff))

