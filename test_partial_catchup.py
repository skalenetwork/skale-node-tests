import os
import time
from base64 import b64decode
import binascii
import pytest
import fcntl
from sktest import LocalStarter, LocalDockerStarter, Node, SChain

#if os.geteuid() != 0:
#    print("Please run with sudo")
#    exit(1)

@pytest.fixture
def schain(request):
    sktest_exe = os.getenv("SKTEST_EXE",
                           "/home/dimalit/skaled/build/skaled/skaled")

    emptyBlockIntervalMs = 1000
    snapshotIntervalSec = 1
    snapshottedStartSeconds = -1
    num_nodes = 4
    shared_space_path = ''

    marker = request.node.get_closest_marker("snapshotIntervalSec")
    if marker is not None:
        snapshotIntervalSec = marker.args[0] 

    marker = request.node.get_closest_marker("snapshottedStartSeconds")
    if marker is not None:
        snapshottedStartSeconds = marker.args[0]

    marker = request.node.get_closest_marker("num_nodes") 
    if marker is not None:
        num_nodes = marker.args[0]

    marker = request.node.get_closest_marker("shared_space_path") 
    if marker is not None:
        shared_space_path = marker.args[0]

    run_container = os.getenv('RUN_CONTAINER')

    nodes = [Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec, bls=True)
             for i in range(num_nodes-1)]
    nodes.append( Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec, bls=True,
              snapshottedStartSeconds=snapshottedStartSeconds) )

    starter = LocalStarter(sktest_exe)

    ch = SChain(
        nodes,
        starter,
        prefill=[1000000000000000000, 2000000000000000000],
        emptyBlockIntervalMs=emptyBlockIntervalMs,
        snapshotIntervalSec=snapshotIntervalSec,
        dbStorageLimit = 100000
    )
    ch.start(start_timeout=0, shared_space_path=shared_space_path)

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

def helper_restart_and_crash(ch, id):
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    print("Restarting n4 with crash flag =", id)

    args = ['--test-enable-crash-at', id]
    starter.restart_node(3, args)
    time.sleep(10)
    if wait_answer(n4.eth) == True:
        bn = n1.eth.blockNumber
        print(f"Waiting n4 to catch up block {bn}")
        wait_block(n4.eth, bn)
        if id == 'OverlayDB_commit_2':
            # need to help it die ;)
            t1 = ch.transaction_obj(_from=0, nonce=0)
            t2 = ch.transaction_obj(_from=1, nonce=0)
            print("Sending 2 transactons")
            n1.eth.sendRawTransaction(t1)
            n1.eth.sendRawTransaction(t2)
            print("Waiting 10 seconds to crash")
            time.sleep(10)
        # rotation-related cases
        elif id not in ['OverlayDB_commit_2', 'insertBlockAndExtras']:
            # wait for rotation
            print("Waiting for rotation")
            b_start = n1.eth.blockNumber
            b_now = b_start
            while b_now-b_start < 25:
                print(b_start, b_now)
                time.sleep(1)
                b_now = n1.eth.blockNumber
        assert(not eth_available(n4.eth))

    print("OK, it's fallen")

def helper_restart_normal_and_check(ch):
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    print("Now starting normally")
    starter.restart_node(3, ['--test-enable-crash-at', 'dont_crash'])
    time.sleep(10)
    assert(wait_answer(n4.eth) == True)

    print("Waiting n4 to catch-up")
    s1 = n1.eth.getLatestSnapshotBlockNumber()
    s4 = n4.eth.getLatestSnapshotBlockNumber()
    while s1 != s4:
        print(s1, s4)
        s1 = n1.eth.getLatestSnapshotBlockNumber()
        s4 = n4.eth.getLatestSnapshotBlockNumber()
        time.sleep(1)

    print("Waiting for 2 snapshos and rotation (25 blocks)")
    s_was = n4.eth.getLatestSnapshotBlockNumber()
    s_now = s_was
    counter = 0
    
    while counter < 2 or s_now-s4 < 25:
        s_now = n4.eth.getLatestSnapshotBlockNumber()
        if s_now > s_was:
            s_was = s_now
            counter += 1
            print(f"Snapshot {s_now}")
        time.sleep(1)

    hash1 = n1.eth.getSnapshotSignature(s_now)['hash']
    hash4 = n4.eth.getSnapshotSignature(s_now)['hash']
    assert( hash1 != '' and len(hash1) == 64 and hash1 == hash4)
    print("hashes are equal")

# For details about crash/commit points in skaled, see
# https://skalelabs.atlassian.net/wiki/spaces/SKALE/pages/2349826055/skaled+disk+activity+crash+resistance

@pytest.mark.parametrize("id", ['OverlayDB_commit_2',
                                'insertBlockAndExtras',
                                'after_remove_oldest',
                                'with_two_keys',
                                'with_two_keys_2',      # HACK
                                'genesis_after_rotate',
                                'after_genesis_after_rotate'
                                ])
def test_basic(schain, id):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    assert(wait_answer(n4.eth))

    # HACK wait for additional rotation prior block rotation (to have really two keys!)
    if id == 'with_two_keys_2':
        id = 'with_two_keys'
        print("Waiting for rotation (25 blocks)")
        bn_start = n4.eth.blockNumber
        bn = bn_start
        while bn - bn_start < 25:
            bn = n4.eth.blockNumber
            print(bn_start, bn)
            time.sleep(1)

    helper_restart_and_crash(ch, id)
    helper_restart_normal_and_check(ch)

@pytest.mark.parametrize("repair_crash_id", ['after_pieces_kill',
                                'after_recover',
                                'fix_bad_rotation',
                                'insertBlockAndExtras',
                                ])
def test_repair(schain, repair_crash_id):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    assert(wait_answer(n4.eth))

    # HACK wait for additional rotation prior block rotation (to have really two keys!)
    print("Waiting for rotation (25 blocks)")
    bn_start = n4.eth.blockNumber
    bn = bn_start
    while bn - bn_start < 25:
        bn = n4.eth.blockNumber
        print(bn_start, bn)
        time.sleep(1)

    helper_restart_and_crash(ch, 'with_two_keys')
    helper_restart_and_crash(ch, repair_crash_id)
    helper_restart_normal_and_check(ch)
