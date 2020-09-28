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
    ch = create_default_chain(num_nodes=2, num_accounts=2, empty_blocks = True)
    ch.start()

    eth1  = ch.nodes[0].eth
    eth2  = ch.nodes[1].eth

    #NOTICE: consensus is won by 2-nd node at block #1 (after that - randomly)

    yield (ch, eth1, eth2)

    ch.stop()

def test_stop_in_block(schain2):
    (ch, eth1, eth2) = schain2

    # 1 stop consensus in node2
    eth2.debugInterfaceCall("SkaleHost trace break drop_bad_transactions")

    time.sleep(2) # allow it to start new block

    ch.stop_node(0)

    time.sleep(20) # wait long for stop if it happens

    # check that it's alive
    delayed1 = ch.node_exited(0) == False

    # continue node2
    eth2.debugInterfaceCall("SkaleHost trace continue drop_bad_transactions")

    assert(delayed1)

    time.sleep(20)          # give it time to stop

    # check that it's not alive
    assert (ch.node_exited(0) == True)

    # 2nd will be terminated after yield()
