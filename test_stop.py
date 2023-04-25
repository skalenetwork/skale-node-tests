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

def timed_stop(ch, i, use_exit_time = False):
    block_before = ch.nodes[i].eth.blockNumber
    print(f"Stopping {i+1} at block {block_before}")

    stop_time = None
    if not use_exit_time:
        ch.stop_node(i)
    else:
        t = ch.nodes[i].eth.getBlock('latest')['timestamp']
        stop_time = t + 2
        ch.nodes[i].eth.setSchainExitTime(stop_time)

    t0 = time.time()
    while not ch.node_exited(i):
        try:
            block_after = ch.nodes[i].eth.blockNumber
        except:
            pass    # ignore exception
        time.sleep(0.1)
    t_total = time.time()-t0
    print(f"{i+1} stopped in {t_total}s at block {block_after}")

    if use_exit_time:
        assert(ch.eth.getBlock(block_after)['timestamp'] >= stop_time and ch.eth.getBlock(block_after-1)['timestamp'] < stop_time)

    return {
        'time': t_total,
        'block_before': block_before,
        'block_after': block_after
    }

# 1 stop when frequently mining blocks
# 2 stop when 1/3 of nodes lagging
# 3 stop without 2/3
def test_stop_ladder(schain4):
    (ch, eth1, eth2, eth3, eth4) = schain4

    wait_block_start(eth4)
    time.sleep(0.5)
    stop_res = timed_stop(ch, 3)
    assert(stop_res['block_after'] > stop_res['block_before'])
    assert(stop_res['time'] < 60*5)

    time.sleep(0.5)
    wait_block_start(eth3)
    stop_res = timed_stop(ch, 2)
    assert(stop_res['block_after'] > stop_res['block_before'])
    assert(stop_res['time'] < 60*5)

    stop_res = timed_stop(ch, 1)
    assert(stop_res['block_after'] == stop_res['block_before'])
    assert(stop_res['time'] < 60*5)

@pytest.mark.emptyBlockIntervalMs(1)
def test_exit_time(schain4):
    (ch, eth1, eth2, eth3, eth4) = schain4
    wait_block_start(eth4)
    time.sleep(0.5)
    stop_res = timed_stop(ch, 3, use_exit_time = True)

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
