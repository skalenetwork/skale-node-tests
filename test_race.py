from sktest_helpers import *
import pytest

def final_check(ch):
    difference = ch.compare_all_states()

    if difference is None:
        print('States on all nodes are consistent')
        print('*** Test passed ***')
    else:
        print("Diffs from state 1:")
        print(dump_node_state(difference))
        print_states_difference(ch)
        print('*** Test failed ***')

    assert(difference is None)

@pytest.fixture
def schain2():
    ch = create_default_chain(num_nodes=2, num_accounts=2)
    ch.start()

    eth1  = ch.nodes[0].eth
    eth2  = ch.nodes[1].eth

    #NOTICE: consensus is won by 2-nd node at block #1 (after that - randomly)

    tx1 = ch.transaction_obj(_from=0, nonce=0)
    tx2 = ch.transaction_obj(_from=1, nonce=0)

    yield (ch, eth1, eth2, tx1, tx2)

    final_check(ch)
    ch.stop()

@pytest.mark.parametrize("receive_before", ["fetch_transactions", "create_block", "import_block", "never"])
def test_bcast(schain2, receive_before):
    (ch, eth1, eth2, tx1, tx2) = schain2

    eth1.callSkaleHost("trace break receive_transaction")

    h1 = eth2.sendRawTransaction(tx1)

    h1 = "0x" + binascii.hexlify(h1).decode("utf-8")

    if receive_before != "never":
        eth1.callSkaleHost("trace break " + receive_before)

    if receive_before != "fetch_transactions":           # force only if 0 txns
        eth1.forceBlock()
    time.sleep(2)

    ############################ receive txns, continue and check ##############################

    eth1.callSkaleHost("trace continue receive_transaction")
    time.sleep(2)

    if receive_before != "never":
        eth1.callSkaleHost("trace continue " + receive_before)
        time.sleep(2)

    # one more block
    eth2.forceBlock()
    eth1.forceBlock()
    time.sleep(2)

    # checks 1

    assert(eth1.blockNumber == 2)
    assert(eth2.blockNumber == 2)
    assert(count_txns(eth1)==1)
    assert(count_txns(eth2)==1)

    # checks 2
    counters = []

    cnt = int(eth1.callSkaleHost("trace count import_consensus_born"))
    counters.append(cnt)

    cnt = int(eth1.callSkaleHost("trace count import_future"))
    counters.append(cnt)

    cnt = int(eth1.callSkaleHost("trace count drop_good"))
    counters.append(cnt)

    cnt = int(eth1.callSkaleHost("trace count drop_bad"))
    counters.append(cnt)

    if receive_before == "fetch_transactions":
        assert( counters == [0, 0, 1, 0] )
    elif receive_before == "create_block":
        assert (counters == [1, 1, 0, 1])
    elif receive_before == "import_block":
        assert (counters == [1, 0, 0, 1])
    elif receive_before == "never":
        assert (counters == [1, 0, 0, 0])
    else:
        assert False

    pass
