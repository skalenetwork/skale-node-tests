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

    run_container = os.getenv('RUN_CONTAINER')
    
    n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs)
    n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs)
    n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs)
    n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs)
    starter = LocalStarter(sktest_exe)
    
    ch = SChain(
        [n1, n2, n3, n4],
        starter,
        prefill=[1000000000000000000, 2000000000000000000],
        emptyBlockIntervalMs=emptyBlockIntervalMs
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

def wait_block(eth, bn):
    print(f"wait_block {eth.blockNumber}/{bn}")
    for _ in range(600):
        if eth.blockNumber == bn:
            break
        time.sleep(0.1)
    else:
        # fail with message:
        assert eth.blockNumber == bn

def test_rpc_start_without_consensus(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    wait_answer(n1.eth)

    wait_block(n1.eth, 20)

    print("Stopping 4th node")
    starter.stop_node(3)
    starter.wait_node_stop(3)

    print("Stopping 3rd node")
    starter.stop_node(2)
    starter.wait_node_stop(2)

    print("Stopping 2nd node")
    starter.stop_node(1)
    starter.wait_node_stop(1)

    bn = n1.eth.blockNumber

    print("Restarting 3rd node")
    starter.start_node_after_stop(2)
    assert wait_answer(n3.eth)

    assert bn == n1.eth.blockNumber == n3.eth.blockNumber

    print("Restarting 4th node")
    starter.start_node_after_stop(3)
    assert wait_answer(n4.eth)

    print("Restarting 2nd node")
    starter.start_node_after_stop(1)
    assert wait_answer(n2.eth)

    time.sleep(10)
    assert bn < n1.eth.blockNumber