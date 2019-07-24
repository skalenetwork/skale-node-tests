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

def test_no_bcast(schain2):
    (ch, eth1, eth2, tx1, tx2) = schain2

    eth2.pauseBroadcast(True)
    eth2.pauseConsensus(True)
    
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

def test_late_bcast(schain2):
    (ch, eth1, eth2, tx1, tx2) = schain2
    
    eth2.pauseBroadcast(True)

    h1 = eth2.sendRawTransaction(tx1)
    h1 = "0x" + binascii.hexlify(h1).decode("utf-8")
    eth1.forceBlock()
    eth2.forceBroadcast(h1)

    time.sleep(2)
    assert(eth1.blockNumber == 1)
    assert(eth2.blockNumber == 1)

    # eth1 should have an extra copy of this txn now, which should be dropped
    eth2.forceBlock()
    eth1.forceBlock()

    time.sleep(2)
    assert(eth1.blockNumber == 2)
    assert(eth2.blockNumber == 2)
    assert(count_txns(eth1)==1)
    assert(count_txns(eth2)==1)

