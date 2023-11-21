from sktest_helpers import *
import pytest

@pytest.fixture
def schain4(request):
    gen = schain_helper(4, request)
    ch = next(gen)
    yield (ch, ch.nodes[0].eth, ch.nodes[1].eth, ch.nodes[2].eth, ch.nodes[3].eth)
    try:
        yield( next(gen) )
    except:
        pass

@pytest.fixture
def schain1(request):
    yield from schain_helper(1, request)

def schain_helper(num_nodes, request):

    emptyBlockIntervalMs = 4000
    marker = request.node.get_closest_marker("emptyBlockIntervalMs") 
    if marker is not None:
        emptyBlockIntervalMs = marker.args[0]

    snapshotIntervalSec = -1
    marker = request.node.get_closest_marker("snapshotIntervalSec")
    if marker is not None:
        snapshotIntervalSec = marker.args[0]

    ch = create_default_chain(num_nodes=num_nodes, num_accounts=2,
        emptyBlockIntervalMs = emptyBlockIntervalMs,
        snapshotIntervalSec=snapshotIntervalSec)
    ch.start()

    marker = request.node.get_closest_marker("cpulimit")
    if marker is not None:
        limit = int(marker.args[0])
        for i in range(0, num_nodes):
            ch.starter.cpulimit(i, limit)

    yield ch

    ch.stop()

def wait_block_start(eth):
    bn = eth.blockNumber
    while eth.blockNumber == bn:
        time.sleep(0.1)

def eth_available(eth):
        try:
            bn = eth.blockNumber
            return True
        except:
            return False

def wait_answer(eth):
    for i in range(40):
        avail = eth_available(eth)
        print(f"available: {avail}")
        if avail:
            return avail
        time.sleep(1)
    return False

@pytest.mark.cpulimit(2)
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

#@pytest.mark.cpulimit(2)
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
    # Use 70 sec timeout to allow for long exit of http server
    print("Note: 3 nodes mining")
    wait_block_start(eth3)
    stop_res = timed_stop(ch, 2, timeout=70)
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
# As http server is exiting long - use this big block interval
@pytest.mark.emptyBlockIntervalMs(19000)
@pytest.mark.cpulimit(2)
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
@pytest.mark.cpulimit(2)
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

@pytest.mark.snapshotIntervalSec(60)
def test_stop_in_snapshot(schain1):
    ch = schain1

    # 100k files requre approx 19 sec of hash computing
    num_files = 500000
    print(f"Creating {num_files} files")
    data_dir = ch.nodes[0].data_dir
    for i in range(0, num_files):
        path = data_dir + "/" + "filestorage" + "/" + f"dummy{i}.txt"
        with open(path, 'w') as file:
            pass

    # 1 wait for snapshot
    print("Waiting for snapshot")
    s0 = ch.eth.getLatestSnapshotBlockNumber()
    s = s0
    while s==s0:
        time.sleep(1)
        s = ch.eth.getLatestSnapshotBlockNumber()
    print(f"Got snapshot {s}")
    
    # 2 search for new snapshot without hash!
    guess = s + 1
    while not os.path.isdir(data_dir+"/snapshots/"+str(guess)) and guess < 1000:
        guess += 1
    assert(guess < 1000)
    print(f"Found new snapshot {guess}")
    s = guess
        
    # 3 send SIGTERM
    ch.starter.stop_node(0)
    ch.starter.wait_node_stop(0)
    print("Node stopped")
    
    # 4 check that hash was not computed
    assert(not os.path.exists(data_dir+f"/snapshots/{s}/snapshot_hash.txt"))
    
    # 5 restart and check that start is ok
    ch.starter.start_node_after_stop(0)
    print("Node restarted")

    wait_answer(ch.eth)

    print("Waiting for snapshot")
    s0 = ch.eth.getLatestSnapshotBlockNumber()
    s = s0
    while s==s0:
        time.sleep(1)
        s = ch.eth.getLatestSnapshotBlockNumber()
    print(f"Got snapshot {s}")

    # do same for hash verification after download

# send SIGTERM while skaled is exiting by exit time
@pytest.mark.emptyBlockIntervalMs(1)
#@pytest.mark.cpulimit(2)
def test_double_stop(schain4):
    (ch, eth1, eth2, eth3, eth4) = schain4

    print("Note: 3 nodes mining")
    eth2.pauseConsensus(True)

    wait_block_start(eth4)

    stop_time = eth4.getBlock('latest')['timestamp']

    block_before = eth4.blockNumber

    print(f"Stopping 4 at block {block_before}")
    print("(using stop_time)")
    eth4.setSchainExitTime(stop_time)

    # should exit here
    wait_block_start(eth4)
    # send additional SIGTERM
    time.sleep(2)
    ch.starter.stop_node(3)

    t0 = time.time()

    while not ch.node_exited(3):
        time.sleep(0.1)

    exit_code = ch.starter.node_exit_code(3)

    t_total = time.time()-t0
    print(f"4 stopped in {t_total}s with exit code {exit_code}")

    assert(exit_code == 0)

    block_after = eth1.blockNumber
    print(f"Block after stop = {block_after}")
    assert(block_after == block_before+1)

    eth2.pauseConsensus(False)

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
