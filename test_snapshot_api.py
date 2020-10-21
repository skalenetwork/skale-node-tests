import os
import time
from base64 import b64decode
import binascii
import pytest
from sktest import LocalStarter, LocalDockerStarter, Node, SChain

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

@pytest.fixture
def schain():
    sktest_exe = os.getenv("SKTEST_EXE",
                           "/home/dimalit/skaled/build-no-mp/skaled/skaled")
    
    emptyBlockIntervalMs = 2000
    snapshotIntervalMs = 1
    
    run_container = os.getenv('RUN_CONTAINER')
    
    n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalMs, bls=True)
    n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalMs, bls=True)
    n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalMs, bls=True)
    n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalMs, bls=True)
    starter = LocalStarter(sktest_exe)
        
    ch = SChain(
        [n1, n2, n3, n4],
        starter,
        prefill=[1000000000000000000, 2000000000000000000],
        emptyBlockIntervalMs=emptyBlockIntervalMs,
        snapshotIntervalMs=snapshotIntervalMs
    )
    ch.start(start_timeout=0)

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
    for i in range(20):
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
        assert -1 == bn

def query_3(eth):
    bn = eth.blockNumber
    s  = eth.getLatestSnapshotBlockNumber()
    snap = eth.getSnapshot(s)
    print(f"{bn} {s} {snap}")
    return (bn, s, snap)
    
def assert_b_s(eth, b, s):
    assert eth.blockNumber == b
    assert eth.getLatestSnapshotBlockNumber() == s

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

    wait_block(n1.eth, 2)
    print("starting from block 2")

    block = 2

    for _ in range(20):

        # delay hash computation on 2 nodes
        print("pausing hash")
        while n1.eth.getLatestSnapshotBlockNumber()  != block-1 or n2.eth.getLatestSnapshotBlockNumber() != block-1:
            pass

        n1.eth.debugInterfaceCall("Client trace break computeSnapshotHash_start")
        n2.eth.debugInterfaceCall("Client trace break computeSnapshotHash_start")
        n1.eth.debugInterfaceCall("Client trace wait computeSnapshotHash_start")
        # warning: cannot wait on n2 because its probably already there!
        
        block = n1.eth.blockNumber
        print(f"block={block} stateRoot={binascii.hexlify(n1.eth.getBlock(block)['stateRoot'])}")
        try:
            ch.transaction_async()
        except:
            pass    # already exists
      
        # wait for proposals
        print(f"(proposals are being created..consenses goes for block {block+1})")
        time.sleep(3)

        # continue
        print("continue")
        n1.eth.debugInterfaceCall("Client trace continue computeSnapshotHash_start")
        n2.eth.debugInterfaceCall("Client trace continue computeSnapshotHash_start")

        
def test_corner_cases(schain):
    ch = schain
    n1 = ch.nodes[0]
        
    wait_answer(n1.eth)
    wait_block(n1.eth, 1)
    assert_b_s(n1.eth, 1, 0)

    # work with snapshot of block 0:
    ch = n1.eth.downloadSnapshotFragment(0, 10)
    assert type(ch) is str  # error

    assert type( n1.eth.getSnapshot(1) ) is str # error
    assert type( n1.eth.getSnapshot(-1) ) is str # error
    assert type( n1.eth.getSnapshotSignature(1) ) is str # error
    assert type( n1.eth.getSnapshotSignature(-1) ) is str # error

    snap = n1.eth.getSnapshot(0)
    assert type(snap) is str         # error
    
    wait_block(n1.eth, 2)
    time.sleep(0.5)                  # compute hash

    assert_b_s(n1.eth, 2, 1)
    snap = n1.eth.getSnapshot(1)
    assert type(snap) is dict        # no error    
    
    data_size = snap['dataSize']
    assert data_size > 0
    ch = n1.eth.downloadSnapshotFragment(0, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10
    
    # now we are in timeout
    assert type( n1.eth.getSnapshot(0) ) is str # error
    assert type( n1.eth.getSnapshot(1) ) is str # error
    assert type( n1.eth.getSnapshot(100) ) is str # error
    
    counter = 0
    while True:
        bn = n1.eth.blockNumber
        assert n1.eth.getLatestSnapshotBlockNumber() >= bn-2
        snap = n1.eth.getSnapshot( bn-2 )
        if type(snap) is dict:
            break
        print(f"Waiting at block {bn}")
        time.sleep(1)
        
        counter += 1
        assert counter < 120    # approx

    data_size = snap['dataSize']
    assert data_size > 0
    ch = n1.eth.downloadSnapshotFragment(0, 10)
    assert len(b64decode(ch['data']))==ch['size'] and ch['size'] == 10

def test_main(schain):
    ch = schain
    n1 = ch.nodes[0]
    
    wait_answer(n1.eth)
    assert type( n1.eth.getSnapshotSignature(0) ) is str    # error
    wait_block(n1.eth, 3)
    time.sleep(1)           # wait for hash
    assert_b_s(n1.eth, 3, 2)
    assert type( n1.eth.getSnapshotSignature(0) ) is str    # error
    assert type( n1.eth.getSnapshotSignature(1) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(2) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(3) ) is str    # error

    # extend hash computation
    n1.eth.debugInterfaceCall("Client trace break computeSnapshotHash_start")
    
    wait_block(n1.eth, 4)
    assert_b_s(n1.eth, 4, 2)
    assert type( n1.eth.getSnapshotSignature(1) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(2) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(3) ) is str    # error
    n1.eth.debugInterfaceCall("Client trace continue computeSnapshotHash_start")
    time.sleep(0.5)
    assert_b_s(n1.eth, 4, 3)
    assert type( n1.eth.getSnapshotSignature(4) ) is str    # error
    assert type( n1.eth.getSnapshotSignature(1) ) is str   # rotated    
    assert type( n1.eth.getSnapshotSignature(2) ) is dict   # ok
    assert type( n1.eth.getSnapshotSignature(3) ) is dict   # ok
    
    snap = n1.eth.getSnapshot(3)
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

def test_wait(schain):
    ch = schain
    n1 = ch.nodes[0]
    #for _ in range(50):
    while True:
        try:
            bn1 = n1.eth.blockNumber
            s1 = n1.eth.getLatestSnapshotBlockNumber()
            print(f"block/snapshot: {bn1} {s1}")            
    
        except Exception as e:
            print(str(e))
            pass
    
        time.sleep(1)
