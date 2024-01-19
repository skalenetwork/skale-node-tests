import os
import time
from base64 import b64decode
import binascii
import pytest
import fcntl
from sktest import LocalStarter, Node, SChain

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

@pytest.fixture
def schain(request):
    sktest_exe = os.getenv("SKTEST_EXE",
                           "/home/dimalit/skaled/build-no-mp/skaled/skaled")
    
    emptyBlockIntervalMs = 2000
    snapshotIntervalSec = 1
    snapshotDownloadTimeout = 60
    snapshotDownloadInactiveTimeout = 60
    snapshottedStartSeconds = -1
    num_nodes = 4
    shared_space_path = ''
    chain_id = None
    sync = False
    historic = False

    marker = request.node.get_closest_marker("snapshotIntervalSec")
    if marker is not None:
        snapshotIntervalSec = marker.args[0]

    marker = request.node.get_closest_marker("snapshotDownloadTimeout")
    if marker is not None:
        snapshotDownloadTimeout = marker.args[0]

    marker = request.node.get_closest_marker("snapshotDownloadInactiveTimeout")
    if marker is not None:
        snapshotDownloadInactiveTimeout = marker.args[0] 
    
    marker = request.node.get_closest_marker("snapshottedStartSeconds")
    if marker is not None:
        snapshottedStartSeconds = marker.args[0]

    marker = request.node.get_closest_marker("num_nodes") 
    if marker is not None:
        num_nodes = marker.args[0]
        
    marker = request.node.get_closest_marker("shared_space_path") 
    if marker is not None:
        shared_space_path = marker.args[0]

    marker = request.node.get_closest_marker("chain_id") 
    if marker is not None:
        chain_id = marker.args[0]

    marker = request.node.get_closest_marker("sync") 
    if marker is not None:
        sync = True

    marker = request.node.get_closest_marker("historic") 
    if marker is not None:
        historic = True

    run_container = os.getenv('RUN_CONTAINER')

    nodes = [Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec)
             for i in range(num_nodes-1)]
    nodes.append( Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec,
              snapshottedStartSeconds=snapshottedStartSeconds) )

    if sync:
        nodes.append( Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec,
              sync=True,
              snapshottedStartSeconds=20) )

    if historic:
        nodes.append( Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec,
              historic=True,
              snapshottedStartSeconds=25) )

    starter = LocalStarter(sktest_exe)

    ch = SChain(
        nodes,
        starter,
        prefill=[1000000000000000000, 2000000000000000000],
        emptyBlockIntervalMs=emptyBlockIntervalMs,
        snapshotIntervalSec=snapshotIntervalSec,
        snapshotDownloadTimeout=snapshotDownloadTimeout,
        snapshotDownloadInactiveTimeout=snapshotDownloadInactiveTimeout,
        dbStorageLimit = 10000000,
        chainID = chain_id,
        schainName = "rhythmic-tegmen",
        bls = True,
        mtm = True
    )
    ch.start(start_timeout=5, shared_space_path=shared_space_path)

    yield(ch)

    print("Exiting")
    ch.stop()

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

def wait_block(eth, bn):
    print(f"wait_block {eth.blockNumber}/{bn}")
    for _ in range(600):
        if eth.blockNumber == bn:
            break
        time.sleep(0.1)
    else:
        # fail with message:
        assert eth.blockNumber == bn
    
def assert_b_s(eth, b, s):
    assert eth.blockNumber == b
    assert eth.getLatestSnapshotBlockNumber() == s

@pytest.mark.snapshottedStartSeconds(90)
@pytest.mark.snapshotIntervalSec(30)
def test_download_download(schain):
    ch = schain
    n1 = ch.nodes[0]    
    n4 = ch.nodes[3]

    time.sleep(70) # wait till 0 snapshot will be downloaded
        
    wait_answer(n4.eth)
    
    s4_initial = n4.eth.getLatestSnapshotBlockNumber()

    counter = 0
    s4 = s4_initial
    while s4 == s4_initial:
        time.sleep(1)        
        s4 = n4.eth.getLatestSnapshotBlockNumber()
        print(f"Waiting for next snapshot: {s4}")
        counter += 1
        
        # wait twice time!
        if counter == 30*2:
            break
    
    # edit here synchronously!
    assert counter < 30*2

    assert type( n4.eth.getSnapshotSignature(s4) ) is dict

    snap = n4.eth.getSnapshot(s4)
    assert type(snap) is dict
    
    data_size = snap['dataSize']
    assert data_size > 0
    ch = n4.eth.downloadSnapshotFragment(0, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10


def test_corner_cases(schain):
    ch = schain
    n1 = ch.nodes[0]
        
    wait_answer(n1.eth)
    wait_block(n1.eth, 3)
    time.sleep(1)
    assert_b_s(n1.eth, 3, 2)

    # 0 snapshot is always present
    assert type( n1.eth.getSnapshotSignature(0) ) is dict # ok

    # work with snapshot of block 1:
    ch = n1.eth.downloadSnapshotFragment(1, 10)
    assert type(ch) is str  # error

    assert type( n1.eth.getSnapshot(3) ) is str # error
    assert type( n1.eth.getSnapshot(4) ) is str # error
    assert type( n1.eth.getSnapshot(-1) ) is str # error
    assert type( n1.eth.getSnapshotSignature(3) ) is str # error
    assert type( n1.eth.getSnapshotSignature(4) ) is str # error
    assert type( n1.eth.getSnapshotSignature(-1) ) is str # error

    snap = n1.eth.getSnapshot(1)
    assert type(snap) is str         # error
    
    wait_block(n1.eth, 4)
    time.sleep(1)                  # time for hash
    assert_b_s(n1.eth, 4, 3)

    snap = n1.eth.getSnapshot(3)
    assert type(snap) is dict        # no error    
    
    data_size = snap['dataSize']
    assert data_size > 0
    ch = n1.eth.downloadSnapshotFragment(0, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10
    
    # now we are in timeout
    assert type( n1.eth.getSnapshot(0) ) is str # error
    assert type( n1.eth.getSnapshot(1) ) is str # error
    assert type( n1.eth.getSnapshot(2) ) is str # error
    assert type( n1.eth.getSnapshot(3) ) is str # error
    assert type( n1.eth.getSnapshot(4) ) is str # error
    assert type( n1.eth.getSnapshot(100) ) is str # error
    
    bn = n1.eth.blockNumber
    time.sleep(0.5)
    s = n1.eth.getLatestSnapshotBlockNumber()
    assert s == bn-1 or s == bn           # can be if bn incremented
    snap = n1.eth.getSnapshot( bn-1 )
    assert(type(snap) is str)             # not yet ready

def test_main(schain):
    ch = schain
    n1 = ch.nodes[0]

    wait_answer(n1.eth)
    wait_block(n1.eth, 1)               # HACK needed for 0 snapshot

    assert type( n1.eth.getSnapshotSignature(0) ) is dict    # ok
    wait_block(n1.eth, 3)
    assert_b_s(n1.eth, 3, 2)

    assert_b_s(n1.eth, 3, 2)    # wait for hash ready but not exposed
    # disallow it to switch to next block
    n1.eth.debugInterfaceCall("SkaleHost trace break create_block")
    assert type( n1.eth.getSnapshotSignature(0) ) is dict    # ok
    assert type( n1.eth.getSnapshotSignature(1) ) is str    # error because 1 is never snapshotted
    assert type( n1.eth.getSnapshotSignature(2) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(3) ) is str    # error

    #wait_block(n1.eth, 4)
    #time.sleep(1)
    # extend hash computation
    n1.eth.debugInterfaceCall("Client trace break computeSnapshotHash_start")

    time.sleep(5)           # this is waiting for tracepoint
    n1.eth.debugInterfaceCall("SkaleHost trace continue create_block")

    wait_block(n1.eth, 4)
    assert_b_s(n1.eth, 4, 3)
    # disallow it to switch to next block
    n1.eth.debugInterfaceCall("SkaleHost trace break create_block")
    assert type( n1.eth.getSnapshotSignature(1) ) is str    # 1 is not snapshotted
    assert type( n1.eth.getSnapshotSignature(2) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(3) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(4) ) is str    # error
    time.sleep(3.0)			# allow snapshot hash to start being computed
    n1.eth.debugInterfaceCall("Client trace continue computeSnapshotHash_start")
    time.sleep(0.5)
    assert_b_s(n1.eth, 4, 3)    # still not exposed
    assert type( n1.eth.getSnapshotSignature(4) ) is str    # error
    assert type( n1.eth.getSnapshotSignature(2) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(3) ) is dict   # ok

    time.sleep(5)           # this is waiting for tracepoint
    n1.eth.debugInterfaceCall("SkaleHost trace continue create_block")

    # check rotation
    wait_block(n1.eth, 5)
    # disallow it to switch to next block
    n1.eth.debugInterfaceCall("SkaleHost trace break create_block")
    assert type( n1.eth.getSnapshotSignature(2) ) is str    # rotated
    assert type( n1.eth.getSnapshotSignature(3) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(4) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(5) ) is str    # error

    time.sleep(5)           # this is waiting for tracepoint
    n1.eth.debugInterfaceCall("SkaleHost trace continue create_block")

    snap = n1.eth.getSnapshot(4)
    assert type(snap) is dict         # no error
    data_size = snap['dataSize']
    
    ch = n1.eth.downloadSnapshotFragment(0, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10
    
    ch = n1.eth.downloadSnapshotFragment(data_size-10, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10
    
    ch = n1.eth.downloadSnapshotFragment(data_size-10, 11)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10
    
    ch = n1.eth.downloadSnapshotFragment(data_size-1, 1)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 1
    
    ch = n1.eth.downloadSnapshotFragment(10, 0)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 0
    
    ch = n1.eth.downloadSnapshotFragment(data_size, 0)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 0
    
    ch = n1.eth.downloadSnapshotFragment(data_size, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 0
    
    ch = n1.eth.downloadSnapshotFragment(data_size+1, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 0

    ch = n1.eth.downloadSnapshotFragment(data_size+1, 0)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 0

    ch = n1.eth.downloadSnapshotFragment(-1, 0)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 0

    ch = n1.eth.downloadSnapshotFragment(-1, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 0


def test_stateRoot_conflict(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    
    wait_answer(n1.eth)
    wait_answer(n2.eth)
    wait_answer(n3.eth)
    wait_answer(n4.eth)

    wait_block(n1.eth, 3)
    print("starting from block 3")

    block = 3

    for _ in range(20):

        # delay hash computation on 2 nodes
        print("pausing hash")
        while n1.eth.getLatestSnapshotBlockNumber()  != block-1 or n2.eth.getLatestSnapshotBlockNumber() != block-1:
            time.sleep(0.1)

        n1.eth.debugInterfaceCall("Client trace break computeSnapshotHash_start")
        n2.eth.debugInterfaceCall("Client trace break computeSnapshotHash_start")
        n1.eth.debugInterfaceCall("Client trace wait computeSnapshotHash_start")
        # warning: cannot wait on n2 because its probably already there!

        block = n1.eth.blockNumber
        print(f"block={block} stateRoot={binascii.hexlify(n1.eth.getBlock(block)['stateRoot'])}")
        # wait for proposals
        print(f"(proposals are being created..consensus goes for block {block+1})")
        try:
            tx = ch.transaction_obj()
            n2.eth.sendRawTransaction(tx)
        except:
            pass    # already exists
      
        # continue
        print("continue")
        n1.eth.debugInterfaceCall("Client trace continue computeSnapshotHash_start")
        n2.eth.debugInterfaceCall("Client trace continue computeSnapshotHash_start")

@pytest.mark.num_nodes(4)
@pytest.mark.snapshotIntervalSec(60)
@pytest.mark.sync
@pytest.mark.historic
#@pytest.mark.chain_id("0xd2ba743e9fef4")
#@pytest.mark.chain_id("0x2")
def test_wait(schain):
    ch = schain
    n1 = ch.nodes[0]
    #for _ in range(50):
    while True:
        try:
            bn1 = n1.eth.blockNumber
            s1 = n1.eth.getLatestSnapshotBlockNumber()
            if bn1 % 10 == 0:
              print(f"block/snapshot: {bn1} {s1}")

        except Exception as e:
            print(str(e))

#        try:
#            tx = ch.transaction_obj()
#            ch.nodes[1].eth.sendRawTransaction(tx)
#        except:
#            pass    # already exists

        time.sleep(1)

@pytest.mark.num_nodes(4) # only 4! (no more keys in config!)
@pytest.mark.snapshotIntervalSec(60)
@pytest.mark.chain_id("0xd2ba743e9fef4")
def test_2_snapshots(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    latest_snapshot = 0
    snapshots_count = 0
    worked = False        # exception can occur only once!
    while True:
        try:
            bn1 = n1.eth.blockNumber
            s1 = n1.eth.getLatestSnapshotBlockNumber()
            print(f"block/snapshot: {bn1} {s1}")

            worked = True

            if s1 != latest_snapshot and latest_snapshot != 0:
                snapshots_count+=1

            latest_snapshot = s1

            # wait 2nd snapshot +1 for sure
            if snapshots_count == 3:
                break

        except Exception as e:
            print(str(e))
            assert(not worked)

        try:
            tx = ch.transaction_obj()
            n2.eth.sendRawTransaction(tx)
        except:
            pass    # already exists

        time.sleep(1)

    # check that skaled is still here
    bn = n1.eth.blockNumber

@pytest.mark.num_nodes(4) # only 4! (no more keys in config!)
@pytest.mark.snapshotIntervalSec(60)
@pytest.mark.snapshotDownloadTimeout(60)
@pytest.mark.snapshotDownloadInactiveTimeout(60)
@pytest.mark.shared_space_path("shared_space")
@pytest.mark.chain_id("0xd2ba743e9fef4")
def test_unlock_shared_space_partial_download(schain):
    try:
        os.mkdir("shared_space")
    except:
        pass

    ch = schain
    n4 = ch.nodes[3]
        
    wait_answer(n4.eth)
    
    s4_initial = n4.eth.getLatestSnapshotBlockNumber()

    counter = 0
    s4 = s4_initial
    while s4 == s4_initial:
        time.sleep(1)        
        s4 = n4.eth.getLatestSnapshotBlockNumber()
        print(f"Waiting for next snapshot: {s4}")
        counter += 1
        
        # wait twice time!
        if counter == 30*2:
            break
    
    # edit here synchronously!
    assert counter < 30*2

    assert type( n4.eth.getSnapshotSignature(s4) ) is dict

    snap = n4.eth.getSnapshot(s4)
    assert type(snap) is dict
    
    data_size = snap['dataSize']
    assert data_size > 0
    ch = n4.eth.downloadSnapshotFragment(0, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10

    time.sleep(90)
    ch = n4.eth.downloadSnapshotFragment(10, 10)
    assert ch == "there's no current snapshot, or snapshot expired; please call skale_getSnapshot() first"

@pytest.mark.num_nodes(4) # only 4! (no more keys in config!)
@pytest.mark.snapshotIntervalSec(60)
@pytest.mark.snapshotDownloadTimeout(60)
@pytest.mark.snapshotDownloadInactiveTimeout(60)
@pytest.mark.shared_space_path("shared_space")
@pytest.mark.chain_id("0xd2ba743e9fef4")
def test_unlock_shared_space_full_download(schain):
    try:
        os.mkdir("shared_space")
    except:
        pass

    ch = schain
    n4 = ch.nodes[3]
        
    wait_answer(n4.eth)
    
    s4_initial = n4.eth.getLatestSnapshotBlockNumber()

    counter = 0
    s4 = s4_initial
    while s4 == s4_initial:
        time.sleep(1)        
        s4 = n4.eth.getLatestSnapshotBlockNumber()
        print(f"Waiting for next snapshot: {s4}")
        counter += 1
        
        # wait twice time!
        if counter == 30*2:
            break
    
    # edit here synchronously!
    assert counter < 30*2

    assert type( n4.eth.getSnapshotSignature(s4) ) is dict

    snap = n4.eth.getSnapshot(s4)
    assert type(snap) is dict
    
    data_size = snap['dataSize']
    max_allowed_chunk_size = snap['maxAllowedChunkSize']
    assert data_size > 0 and max_allowed_chunk_size > 0
    for i in range((data_size + max_allowed_chunk_size - 1) // max_allowed_chunk_size ):
        ch = n4.eth.downloadSnapshotFragment(max_allowed_chunk_size * i, max_allowed_chunk_size)
        assert len(b64decode(ch['data']))==ch['size'] and ch['size'] <= max_allowed_chunk_size

    time.sleep(90)
    ch = n4.eth.downloadSnapshotFragment(10, 10)
    assert ch == "there's no current snapshot, or snapshot expired; please call skale_getSnapshot() first"

@pytest.mark.num_nodes(1)
@pytest.mark.shared_space_path("shared_space")
def test_shared_space(schain):
    try:
        os.mkdir("shared_space")
    except:
        pass
    ch = schain
    n = ch.nodes[0]
    eth = n.eth
    assert(wait_answer(eth))
    wait_block(eth, 3)
    with open("shared_space/.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        snap = eth.getSnapshot(2)
        assert(type(snap) is str and snap.find("occupied") >= 0)
    snap = eth.getSnapshot(2)
    assert(type(snap) is dict)
    for t in (0, 2):
        print(f"sleeping {t}")
        time.sleep(t)
        with open("shared_space/.lock", "w") as f:
            try:            
                fcntl.flock(f, fcntl.LOCK_EX|fcntl.LOCK_NB)
                assert(false)
            except BlockingIOError as ex:
                # busy
                snap = eth.getSnapshot(2)
                assert(type(snap) is str)
                
@pytest.mark.shared_space_path("shared_space")
def test_download_lock(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    eth = n1.eth
    assert(wait_answer(eth))
    wait_block(eth, 5)
    bn1 = n1.eth.blockNumber
    s1 = n1.eth.getLatestSnapshotBlockNumber()
    print(f"block/snapshot: {bn1} {s1}")
    
    try:
        os.mkdir("shared_space")
    except:
        pass
    
    with open("shared_space/.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        
        print("Restarting n4")
    
        args = []
        args.append("--download-snapshot")
        args.append("http://" + ch.nodes[0].bindIP + ":" + str(ch.nodes[0].basePort + 3))  # noqa
        starter.restart_node(3, args)
        wait_answer(n4.eth)
