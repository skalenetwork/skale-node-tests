import os
import time
import pytest
import binascii
import shutil
from sktest import LocalStarter, Node, SChain

if os.geteuid() != 0:
    print("Please run with sudo")
    exit(1)

@pytest.fixture
def schain(request):
    sktest_exe = os.getenv("SKTEST_EXE",
                           "/home/dimalit/skaled/build-no-mp/skaled/skaled")
    
    emptyBlockIntervalMs = 1000
    snapshotIntervalSec = 1
    snapshottedStartSeconds = -1
    requireSnapshotMajority = True
    
    marker = request.node.get_closest_marker("snapshotIntervalSec") 
    if marker is not None:
        snapshotIntervalSec = marker.args[0] 
    
    marker = request.node.get_closest_marker("snapshottedStartSeconds") 
    if marker is not None:
        snapshottedStartSeconds = marker.args[0]
    
    marker = request.node.get_closest_marker("requireSnapshotMajority")
    if marker is not None:
        requireSnapshotMajority = marker.args[0]

    run_container = os.getenv('RUN_CONTAINER')
    
    n1 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec)
    n2 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec)
    n3 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec)
    n4 = Node(emptyBlockIntervalMs=emptyBlockIntervalMs,
              snapshotInterval=snapshotIntervalSec,
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
            
            if bn1 == 10 and s1 == bn1-1:
                
                need_sleep = False
                
                if not have_others:                                                               
                    # wait till they delete block 4
                    n1.eth.debugInterfaceCall("SkaleHost trace break create_block")
                    need_sleep = True
                
                if have_others != have_4:
                    # stop n4:it will have queried block if not have_others
                    # and not have if have_others
                    while n4.eth.blockNumber != bn1 or n4.eth.getLatestSnapshotBlockNumber() != bn1-1:
                        time.sleep(0.1)
                    n4.eth.debugInterfaceCall("SkaleHost trace break create_block")
                    need_sleep = True
                
                if need_sleep:
                    print("Sleep 15")
                    time.sleep(15)   # for 3 blocks
            
                # possibly it will generate one more block
                if have_others != have_4:
                    n4.eth.debugInterfaceCall("SkaleHost trace continue create_block")
                
                # use this case to test retry
                # if not have_4 and have_others:
                #     n1.eth.getSnapshot(n1.eth.blockNumber-2)
                
                print("Restarting")
                
                # restart n4    
                args = []
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
                
                if not avail:
                    break
    
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

@pytest.mark.snapshotIntervalSec(40)
def test_restart(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    for _ in range(200):
    #while True:
        try:
            bn1 = n1.eth.blockNumber
            bn2 = n2.eth.blockNumber
            bn3 = n3.eth.blockNumber
            bn4 = n4.eth.blockNumber
            print(f"blockNumber's: {bn1} {bn2} {bn3} {bn4}")
            
            block = n1.eth.blockNumber
            print(f"block={block} stateRoot={binascii.hexlify(n1.eth.getBlock(block)['stateRoot'])}")
            try:
                ch.transaction_async()
            except:
                pass    # already exists
            
            s1 = n1.eth.getLatestSnapshotBlockNumber()
            s4 = n4.eth.getLatestSnapshotBlockNumber()
            print(f"s1 = {s1} s4 = {s4}")        
            
            if bn1 == bn4:
                assert s1 == s4
            
            if s1 != 0 and bn4 == bn1 and bn1 >= 10:
                                
                print("Restarting")
                
                # restart n4    
                starter.restart_node(3, [])
                
                # to be sure it really restarted
                time.sleep(5)
                assert not eth_available(n4.eth)
                
                avail = wait_answer(n4.eth)
                assert avail
                time.sleep(10)
        
            if bn1 >= 60 and bn1==bn2 and bn2==bn3 and bn3==bn4:
                break
    
        except Exception as e:
            print(str(e))
            pass
    
        time.sleep(1)
    else:
        assert False

@pytest.mark.snapshotIntervalSec(60)
@pytest.mark.snapshottedStartSeconds(30)
def test_download_early(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    avail = wait_answer(n4.eth)
    print(f"n1's block number = {n1.eth.blockNumber}")
    assert avail
    print(f"n4's block number = {n4.eth.blockNumber}")
    
    for _ in range(50):
        bn1 = n1.eth.blockNumber
        bn4 = n4.eth.blockNumber
        print(f"{bn1} {bn4}")
        time.sleep(1)

    assert abs(bn1-bn4)<=1
    assert n1.eth.getLatestSnapshotBlockNumber() != "earliest"

@pytest.mark.parametrize("who, from_who", [(1, 2), (0, 1), (1, 3), (0, 3), (1, 0), (3, 0)])
@pytest.mark.snapshottedStartSeconds(50)
@pytest.mark.snapshotIntervalSec(1)
def test_download_download(schain, who, from_who):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    avail = wait_answer(n4.eth)
    print("Started n4")
    print(f"n1's block number = {n1.eth.blockNumber}")
    assert avail
    print(f"n4's block number = {n4.eth.blockNumber}")

    for _ in range(50):
        bn1 = n1.eth.blockNumber
        bn2 = n2.eth.blockNumber
        bn3 = n3.eth.blockNumber
        bn4 = n4.eth.blockNumber

        print(f"{bn1} {bn2} {bn3} {bn4}")

        if bn1==bn2 and bn2==bn3 and bn3==bn4:
            break

        time.sleep(1)
    else:
        assert False

    # restart who!
    print(f"Restarting n{who+1}")

    args=[]
    if who!=3:
        args = []
        args.append("--download-snapshot")
        args.append("http://" + ch.nodes[from_who].bindIP + ":" + str(ch.nodes[from_who].basePort + 13))
    starter.restart_node(who, args, 10)
    
    
    # to be sure it really restarted
    time.sleep(5)
    assert not eth_available(ch.nodes[who].eth)

    avail = wait_answer(ch.nodes[who].eth)
    assert avail
    print(f"Started n{who+1}")

    for _ in range(50):
        bn1 = n1.eth.blockNumber
        bn2 = n2.eth.blockNumber
        bn3 = n3.eth.blockNumber
        bn4 = n4.eth.blockNumber

        print(f"{bn1} {bn2} {bn3} {bn4}")

        if bn1 >= 10 and bn1==bn2 and bn2==bn3 and bn3==bn4:
            break

        time.sleep(1)

    assert abs(bn1-bn4)<=1
    assert abs(bn2-bn4)<=1
    assert n1.eth.getLatestSnapshotBlockNumber() != "earliest"
    assert n2.eth.getLatestSnapshotBlockNumber() != "earliest"
    assert n4.eth.getLatestSnapshotBlockNumber() != "earliest"
    
@pytest.mark.snapshotIntervalSec(40)
def test_late_join(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    
    #ch.transaction()
    
    print("Restarting")
    starter.restart_node(3, [], 200)

    for _ in range(200):
    #while True:
        try:
            bn1 = n1.eth.blockNumber
            bn2 = n2.eth.blockNumber
            bn3 = n3.eth.blockNumber
            bn4 = n4.eth.blockNumber
            print(f"blockNumber's: {bn1} {bn2} {bn3} {bn4}")
                    
            if bn1 >= 60 and bn1==bn2 and bn2==bn3 and bn3==bn4:
                break
    
        except Exception as e:
            print(str(e))
            pass
    
        time.sleep(1)
    else:
        assert False

@pytest.mark.snapshotIntervalSec(10)
@pytest.mark.snapshottedStartSeconds(60)
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

@pytest.mark.snapshotIntervalSec(10)
@pytest.mark.snapshottedStartSeconds(40)
@pytest.mark.requireSnapshotMajority(True)
def test_download_with_majority(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter

    time.sleep(40)

    avail = wait_answer(n4.eth)
    print(f"n1's block number = {n1.eth.blockNumber}")
    assert avail
    print(f"n4's block number = {n4.eth.blockNumber}")

    for _ in range(50):
        bn1 = n1.eth.blockNumber
        bn2 = n2.eth.blockNumber
        bn3 = n3.eth.blockNumber
        bn4 = n4.eth.blockNumber

        print(f"{bn1} {bn2} {bn3} {bn4}")

        if bn1==bn2 and bn2==bn3 and bn3==bn4:
            break

        time.sleep(1)
    else:
        assert False

@pytest.mark.snapshotIntervalSec(10)
def test_wrong_stateRoot_in_proposal(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    
    dummy_hash = "11bbe8db4e347b4e8c937c1c8370e4b5ed33adb3db69cbdb7a38e1e50b1b82fa"
    # dec: 8021325944645810444600318958160784541777644290714340452591235899924003128058
    
    print("Starting 4 nodes")
    #wait_answer(n4.eth)
    #print("Stopping n4")
    #starter.stop_node(3)
    #starter.wait_node_stop(3)    
    
    
    assert( wait_answer(n3.eth) )
    
    path = n3.data_dir + "/filestorage"
    with open(path+"/dummy_file.txt", "w") as f:
        f.write("dummy data\n")
    print("Breaking filestorage hash in "  +path)
    
    old_bn3 = 0
    hang_counter = 0
    
    path = ""
    while True:
        try:
            bn3 = n3.eth.blockNumber
            print(f"bn3={bn3}")
            
            if bn3 >= 50:
                break
            
            # s3 = n3.eth.getLatestSnapshotBlockNumber()
            if bn3 != old_bn3:
                old_bn3 = bn3
                hang_counter = 0
        except:
            # check n1 if n3 crashed
            time.sleep(3)
            assert(eth_available(n1.eth))
            print("Restarting n3 (crashed)")
            starter.restart_node(2, ["--download-snapshot", "http://127.0.0.1:9999"])
            assert( wait_answer(n3.eth) )
            print("n3 should be fixed now")
            
            # avail = wait_answer(n4.eth)
            print("Stopping n4")
            starter.stop_node(3)
            starter.wait_node_stop(3)            

        try:
            ch.transaction_async()
        except:
            pass    # already exists
            
        assert(hang_counter < 45)
            
        time.sleep(1)
        hang_counter += 1
        
@pytest.mark.snapshotIntervalSec(300)
def test_getSnapshot_timeout(schain):
    ch = schain
    n1 = ch.nodes[0]
    n2 = ch.nodes[1]
    n3 = ch.nodes[2]
    n4 = ch.nodes[3]
    starter = ch.starter
    
    print("Starting 4 nodes")
    
    assert( wait_answer(n1.eth) )
    
    print("Waiting for available snapshot")
    snapshot_bn = 0
    while snapshot_bn == 0:
        snapshot_bn = n1.eth.getLatestSnapshotBlockNumber()
        time.sleep(1)
    while snapshot_bn != n2.eth.getLatestSnapshotBlockNumber():
        time.sleep(1)
    while snapshot_bn != n3.eth.getLatestSnapshotBlockNumber():
        time.sleep(1)
    while snapshot_bn != n4.eth.getLatestSnapshotBlockNumber():
        time.sleep(1)
    
    print(f"Filling data_dir with data")
    
    for n in ch.nodes[:3]:
        path = n.data_dir + f"/filestorage/dummy.dat"
        print(path)
        res=os.system(f"dd if=/dev/zero of={path} bs=1M count=1")

    print("3 files finished")

    print("Waiting n4 to crash")
    while wait_answer(n4.eth):
        time.sleep(10)
    print("Success")

    print("Waiting 1 snapshot")
    time.sleep(300)

    print("Restarting n4 from snapshot")
    starter.restart_node(3, ["--download-snapshot", "ddduuummmyyy"])
    time.sleep(120)
    assert( wait_answer(n4.eth) )
    print("Now check how much time skale_getSnapshot took!")
    
