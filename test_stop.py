from sktest_helpers import *
import pytest

@pytest.fixture
def schain4(request):

    emptyBlockIntervalMs = 4000
    marker = request.node.get_closest_marker("emptyBlockIntervalMs") 
    if marker is not None:
        emptyBlockIntervalMs = marker.args[0]

    ch = create_default_chain(num_nodes=4, num_accounts=2, emptyBlockIntervalMs = emptyBlockIntervalMs)
    ch.start()

    eth1  = ch.nodes[0].eth
    eth2  = ch.nodes[1].eth
    eth3  = ch.nodes[2].eth
    eth4  = ch.nodes[3].eth

    yield (ch, eth1, eth2, eth3, eth4)

    ch.stop()

def wait_block_start(eth):
    bn = eth.blockNumber
    while eth.blockNumber == bn:
        time.sleep(0.1)

def timed_stop(ch, i, stop_time = None, timeout=20):

    print(f"pauseConsensus(True)")
    ch.nodes[0].eth.pauseConsensus(True)

    block_before = ch.nodes[i].eth.blockNumber

    print("Transaction")
    try:
        ch.transaction_async()
    except Exception as ex:
        print(repr(ex))

    print(f"Stopping {i+1} at block {block_before}")

    if stop_time:
        print("(using stop_time)")
        ch.nodes[i].eth.setSchainExitTime(stop_time)
    else:
        ch.stop_node(i)

    t0 = time.time()

    if timeout > 0:
        print(f"Sleep {timeout}")
        time.sleep(timeout)
    print(f"pauseConsensus(False)")
    ch.nodes[0].eth.pauseConsensus(False)

    while not ch.node_exited(i):
        time.sleep(0.1)

    t_total = time.time()-t0
    print(f"{i+1} stopped in {t_total}s")

    return {
        'time': t_total,
        'block_before': block_before,
    }

def test_stop_ladder(schain4):
    (ch, eth1, eth2, eth3, eth4) = schain4

    # 1 stop inside block creation
    # should exit on next block
    print("Note: 3 nodes mining")
    eth2.pauseConsensus(True)
    wait_block_start(eth4)
    time.sleep(0.5)
    stop_res = timed_stop(ch, 3)
    block_after = eth3.blockNumber
    print(f"Block after stop = {block_after}")
    eth2.pauseConsensus(False)
    assert(block_after - 1 == stop_res['block_before'])
    assert(stop_res['time'] < 60*5)

    # let 1st transaction be mined
    wait_block_start(eth1)
    wait_block_start(eth1)

    # 2 stop by timeout
    # while 3 nodes are up,
    # consensus should exit before creating next block
    print("Note: 3 nodes mining")
    wait_block_start(eth3)
    stop_res = timed_stop(ch, 2, timeout=40)
    block_after = eth1.blockNumber
    print(f"Block after stop = {block_after}")
    assert(block_after == stop_res['block_before'])
    assert(stop_res['time'] < 60*5)

    # 3 stop totally stuck chain
    print("Note: 2 nodes mining")
    stop_res = timed_stop(ch, 1)
    block_after = eth1.blockNumber
    print(f"Block after stop = {block_after}")
    assert(block_after == stop_res['block_before'])
    assert(stop_res['time'] < 60*5)

# Exit while waiting for new transactions
def test_in_queue(schain4):
    (ch, eth1, eth2, eth3, eth4) = schain4

    eth2.pauseConsensus(True)

    wait_block_start(eth4)

    block_before = eth4.blockNumber
    t0 = time.time()

    print(f"Stopping 4 at block {block_before}, while getting transactions for next")
    ch.stop_node(3)

    while not ch.node_exited(3):
        time.sleep(0.1)

    t_total = time.time()-t0
    print(f"4 stopped in {t_total}s")

    block_after = eth3.blockNumber
    print(f"Block after stop = {block_after}")

    eth2.pauseConsensus(False)

    assert(block_after  == block_before)
    assert(t_total < 60*5)

@pytest.mark.emptyBlockIntervalMs(1)
def test_exit_time(schain4):
    (ch, eth1, eth2, eth3, eth4) = schain4

    print("Note: 3 nodes mining")
    eth2.pauseConsensus(True)
    wait_block_start(eth4)
    time.sleep(0.5)
    stop_time = eth4.getBlock('latest')['timestamp'] + 2
    stop_res = timed_stop(ch, 3, stop_time = stop_time)
    block_after = eth1.blockNumber
    print(f"Block after stop = {block_after}")
    eth2.pauseConsensus(False)
    assert(ch.eth.getBlock(block_after)['timestamp'] >= stop_time and ch.eth.getBlock(block_after-1)['timestamp'] < stop_time)

def excluded_test_stop_in_block(schain4):
    (ch, eth1, eth2, eth3, eth4) = schain4

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
