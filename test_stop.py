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

    yield (ch, eth1, eth2)

    final_check(ch)
    ch.stop()

def test_stop_in_block(schain2):
    (ch, eth1, eth2) = schain2

    # 1 stop consensus in both
    eth1.callSkaleHost("trace break drop_bad_transactions")
    eth2.callSkaleHost("trace break drop_bad_transactions")
    b1 = eth1.blockNumber

    # 2 continue till new block
    eth1.callSkaleHost("trace break create_block")
    eth1.callSkaleHost("trace continue drop_bad_transactions")

    time.sleep(2) # allow it to start new block
    ch.stop_node(0)
    time.sleep(10) # wait long for stop if it happens

    # continue node2
    eth2.callSkaleHost("trace continue drop_bad_transactions")

    eth1.callSkaleHost("trace wait create_block")   # will throw if it's stopped
    b2 = eth1.blockNumber

    assert(b2 == b1 + 1)

    eth1.callSkaleHost("trace continue create_block")

    # TODO check that node1 has exited

    pass
