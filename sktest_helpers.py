import json
import os
import pickle
import time

from hexbytes import HexBytes

from web3.auto import w3
from sktest import list_differences, \
    LocalStarter, ManualStarter, Node, \
    SChain, safe_input_with_timeout

# w3.eth.enable_unaudited_features()


BASE_PORT = 10000
PORT_RANGE = 11

global sktest_exe
# sktest_exe = os.getenv("SKTEST_EXE",
#                        "/home/dimalit/skale-ethereum/scripts/aleth")
sktest_exe = os.getenv("SKTEST_EXE",
                       "/home/dimalit/skaled/build-no-mp/skaled/skaled")


class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)


def dump_node_state(obj):
    return json.dumps(obj, indent=1, cls=HexJsonEncoder)


def create_custom_chain(num_nodes=2, num_accounts=2, empty_blocks=True,
                        rotate_after_block=-1,
                        config_file=None, chainID=None, same_ip=False,
                        run_container=False, bls=False):
    if config_file == None:
        config_file = "config_base.json"

    dbStorageLimit = -1
    # VERY empiric formula %)
    # (specially for test_rotation.py test)
    if rotate_after_block > 0:
        dbStorageLimit = (612+1322)*rotate_after_block*5+2000 # 2k is empirical %)
        dbStorageLimit = int(dbStorageLimit)

    nodes = []
    balances = []

    base_ports = [BASE_PORT + PORT_RANGE * i for i in range(num_nodes)]
    for i, port in enumerate(base_ports):
        emptyBlockIntervalMs = -1
        if empty_blocks:
            emptyBlockIntervalMs = 1000
        if run_container or same_ip:
            node = Node(
                emptyBlockIntervalMs=emptyBlockIntervalMs,
                bindIP='0.0.0.0',
                basePort=port, bls=bls
            )
        else:
            base_port = 1231
            node = Node(bindIP=f'127.0.0.{i+1}', basePort=base_port,
                        emptyBlockIntervalMs=emptyBlockIntervalMs,
                        bls=bls)

        nodes.append(node)

    for node in nodes:
        assert node.sChain is None

    for i in range(num_accounts):
        balances.append(str((i + 1) * 1000000000000000000000))

    config = None
    with open(config_file, "r") as f:
        config = json.load(f)
        print(f"Loaded {config_file}")

    if chainID is None:
        chainID = "0x1"

    global sktest_exe
    #starter = ManualStarter(config)
    starter = LocalStarter(sktest_exe, config)

    emptyBlockIntervalMs = -1
    if empty_blocks:
        emptyBlockIntervalMs = 1000

    chain = SChain(nodes, starter, balances,
                   emptyBlockIntervalMs=emptyBlockIntervalMs, chainID=chainID,
                   dbStorageLimit=dbStorageLimit)

    return chain


def create_default_chain(num_nodes=2, num_accounts=2, empty_blocks=True,
                         config_file=None):
    run_container = os.getenv('RUN_CONTAINER')
    return create_custom_chain(num_nodes, num_accounts, empty_blocks, -1,
                               config_file,
                               run_container=run_container)


def create_chain_with_id(num_nodes=2, num_accounts=2, empty_blocks=True,
                         chain_id=None):
    run_container = os.getenv('RUN_CONTAINER')
    return create_custom_chain(num_nodes, num_accounts, empty_blocks, -1,
                               None, chain_id, run_container=run_container)


def load_private_keys(path, password, count=0):
    # TODO Exceptions?!
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
    except Exception:
        ch.wait_start()
        print("Generating txns")
        for i in range(nTxns):
            acc1 = i % nAcc
            acc2 = (i+1) % nAcc
            nonce = i // nAcc
            print("from=%d nonce=%d %s" % (acc1, nonce, ch.accounts[acc1]))
            txn_str = ch.transaction_obj(value=1,
                                         _from=acc1, to=acc2, nonce=nonce)
            transactions.append(txn_str)
        safe_input_with_timeout("Sending txns - press", 10)
        with open(file, "wb") as fd:
            pickle.dump(transactions, fd)

    return transactions


def wait_for_txns(ch, nTxns, t1=0):
    count = 0
    from_block = 0

    while count < nTxns:

        do_not_print = False
        while True:
            try:
                to_block = ch.eth.blockNumber
                n = 0
                for i in range(from_block, to_block+1):
                    b = ch.eth.getBlock(i)
                    n += len(b.transactions)
                count += n
                from_block = to_block + 1
                break
            except Exception as e:
                if not do_not_print:
                    print(e)
                do_not_print = True

        t2 = time.time()

        if t2 != t1:
            print("%d txns %d blocks" % (count, ch.eth.blockNumber), end=' ')
            if t1 > 0:
                print("perf = %f tx/sec" % (count / (t2 - t1)), end='')
            print()

        time.sleep(1)

    t2 = time.time()

    return t2 - t1


def wait_for_blocks(ch, nBlocks):
    t1 = time.time()
    count = 0

    while count < nBlocks:

        while True:
            try:
                count = ch.eth.blockNumber
                break
            except Exception as e:
                print(e)

        t2 = time.time()

        if t2 != t1:
            print("%d blocks rate = %f blocks/sec" % (count, count/(t2-t1)))

        time.sleep(1)

    t2 = time.time()

    return t2 - t1


def print_states_difference(ch):
    nNodes = len(ch.nodes)
    states = [ch.state(index) for index in range(nNodes)]
    for a_index in range(nNodes):
        for b_index in range(a_index + 1, nNodes):
            diff = list_differences(states[a_index], states[b_index])
            if diff:
                print(f'\nDifference between node '
                      f'#{a_index + 1} and #{b_index + 1}')
                print('\n'.join(diff))
