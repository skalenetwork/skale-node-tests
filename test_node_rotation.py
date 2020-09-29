import os
import time
import pytest
from sktest import LocalStarter, LocalDockerStarter, Node, SChain

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

@pytest.fixture
def schain():
    sktest_exe = os.getenv("SKTEST_EXE",
                           "/home/dimalit/skaled/build-no-mp/skaled/skaled")
    
    emptyBlockIntervalMs = 1000
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

@pytest.mark.parametrize("have_others,have_4", [(True, False), (True, True), (False, False), (False, True)])
# whether we have requested block on all other nodes and on local (#4) node
def test_download_snapshot(schain, have_others, have_4):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    for _ in range(50):
        try:
            bn1 = n1.eth.blockNumber
            bn2 = n2.eth.blockNumber
            bn3 = n3.eth.blockNumber
            bn4 = n4.eth.blockNumber
            print(f"blockNumber's: {bn1} {bn2} {bn3} {bn4}")
            
            s1 = n1.eth.getLatestSnapshotBlockNumber()
            print(f"s1 = {s1}")        
            
            if bn1 == 3 and s1 == str(bn1-1):
                
                need_sleep = False
                
                if not have_others:                                                               
                    # wait till they delete block 4
                    n1.eth.debugInterfaceCall("SkaleHost trace break create_block")
                    need_sleep = True
                
                if have_others != have_4:
                    # stop n4:it will have queried block if not have_others
                    # and not have if have_others
                    while n4.eth.blockNumber != bn1 or n4.eth.getLatestSnapshotBlockNumber() != str(bn1-1):
                        time.sleep(0.1)
                    n4.eth.debugInterfaceCall("SkaleHost trace break create_block")
                    need_sleep = True
                
                if need_sleep:
                    time.sleep(15)   # for 3 blocks
            
                # possibly it will generate one more block
                if have_others != have_4:
                    n4.eth.debugInterfaceCall("SkaleHost trace continue create_block")
                
                # restart n4    
                args = ['--public-key', '18219295635707015937645445755505569836731605273220943516712644721479866137366:13229549502897098194754835600024217501928881864881229779950780865566962175067:3647833147657958185393020912446135601933571182900304549078758701875919023122:2426298721305518429857989502764051546820660937538732738470128444404528302050']
                args.append("--download-snapshot")
                args.append("http://" + ch.nodes[0].bindIP + ":" + str(ch.nodes[0].basePort + 3))  # noqa
                starter.restart_node(3, args)
                
                # to be sure it really restarted
                time.sleep(5)
                assert not eth_available(n4.eth)
                
                # should break if no others
                avail = wait_answer(n4.eth)
    
                if not have_others:                                                               
                    n1.eth.debugInterfaceCall("SkaleHost trace continue create_block")
    
                assert avail == have_others
    
            if bn1 >= 10 and bn1==bn2 and bn2==bn3 and bn3==bn4:
                assert have_others
                break
    
        except Exception as e:
            print(str(e))
            pass
    
        time.sleep(1)
    else:
        # we exit by counter if n4 breaks
        assert not have_others