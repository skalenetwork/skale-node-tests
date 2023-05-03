import os
import time
import pytest
import binascii
import shutil
from sktest import LocalStarter, Node, SChain

@pytest.fixture
def schain(request):
    sktest_exe = os.getenv("SKTEST_EXE",
                           "/home/dimalit/skaled/build-no-mp/skaled/skaled")
    
    emptyBlockIntervalMs = 1000
    snapshotIntervalSec = 1
    snapshottedStartSeconds = -1
    requireSnapshotMajority = True
    downloadGenesisState = True

    marker = request.node.get_closest_marker("snapshotIntervalSec") 
    if marker is not None:
        snapshotIntervalSec = marker.args[0]

    marker = request.node.get_closest_marker("requireSnapshotMajority")
    if marker is not None:
        requireSnapshotMajority = marker.args[0]
    
    marker = request.node.get_closest_marker("snapshottedStartSeconds") 
    if marker is not None:
        snapshottedStartSeconds = marker.args[0]

    run_container = os.getenv('RUN_CONTAINER')
    
    n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec)
    n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec)
    n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec)
    n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec,
              downloadGenesisState=downloadGenesisState,
              snapshottedStartSeconds=snapshottedStartSeconds,
              requireSnapshotMajority=requireSnapshotMajority)
    starter = LocalStarter(sktest_exe)
    
    ch = SChain(
        [n1, n2, n3, n4],
        starter,
        prefill=[1000000000000000000, 2000000000000000000],
        emptyBlockIntervalMs=emptyBlockIntervalMs,
        snapshotIntervalSec=snapshotIntervalSec,
	    bls = True
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
    for i in range(40):
        avail = eth_available(eth)
        print(f"available: {avail}")
        if avail:
            return avail
        time.sleep(1)
    return False

@pytest.mark.snapshotIntervalSec(10)
@pytest.mark.snapshottedStartSeconds(60)
@pytest.mark.downloadGenesisState(True)
def test_download(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    time.sleep(40)

    print(f"n1's block number = {n1.eth.blockNumber}")
    assert n1.eth.blockNumber > 0

    starter.stop_node(1)

    avail = wait_answer(n4.eth)
    print(f"n1's block number = {n1.eth.blockNumber}")
    assert avail
    print(f"n4's block number = {n4.eth.blockNumber}")

    for _ in range(50):
        bn1 = n1.eth.blockNumber
        bn3 = n3.eth.blockNumber
        bn4 = n4.eth.blockNumber

        print(f"{bn1} {bn3} {bn4}")

        if bn1==bn3 and bn3==bn4:
            break

        time.sleep(1)
    else:
        assert False

@pytest.mark.snapshotIntervalSec(10)
@pytest.mark.snapshottedStartSeconds(60)
@pytest.mark.downloadGenesisState(True)
@pytest.mark.requireSnapshotMajority(False)
def test_download_without_majority(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    time.sleep(40)

    print(f"n1's block number = {n1.eth.blockNumber}")
    assert n1.eth.blockNumber > 0

    starter.stop_node(1)

    avail = wait_answer(n4.eth)
    print(f"n1's block number = {n1.eth.blockNumber}")
    assert avail
    print(f"n4's block number = {n4.eth.blockNumber}")

    for _ in range(50):
        bn1 = n1.eth.blockNumber
        bn3 = n3.eth.blockNumber
        bn4 = n4.eth.blockNumber

        print(f"{bn1} {bn3} {bn4}")

        if bn1==bn3 and bn3==bn4:
            break

        time.sleep(1)
    else:
        assert False