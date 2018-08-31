from tempfile import TemporaryDirectory
import os
import io
import json
from subprocess import Popen

def _compare_states(nodes):
    # n[i].eth.blockNumber()
    # n[i].eth.getBlock(j)

    # n[i].eth.getBalance(n[i].accounts[j])
    # n[i].eth.getTransactionCount(n[i].accounts[j])
    # n[i].eth.getCode(n[i].accounts[j])

    # n[i].eth.getTransaction(hash)

    # n[i].eth.getTransactionReceipt(hash)
    pass

def Config(other={}):
    """Simple function that returns default config as a python dictionary and optionally appends it from the dictionary passed."""

    self = {}
    self["sealEngine"] = "Ethash"
    self["params"] = {
        "accountStartNonce": "0x00",
        "homesteadForkBlock": "0x0",
        "daoHardforkBlock": "0x0",
        "EIP150ForkBlock": "0x0",
        "EIP158ForkBlock": "0x0",
        "byzantiumForkBlock": "0x0",
        "constantinopleForkBlock": "0x0",
        "networkID": "12313219",
        "chainID": "0x01",
        "maximumExtraDataSize": "0x20",
        "tieBreakingGas": False,
        "minGasLimit": "0x1388",
        "maxGasLimit": "7fffffffffffffff",
        "gasLimitBoundDivisor": "0x0400",
        "minimumDifficulty": "0x020000",
        "difficultyBoundDivisor": "0x0800",
        "durationLimit": "0x0d",
        "blockReward": "0x4563918244F40000"
    }
    self["genesis"] = {
        "nonce": "0x0000000000000042",
        "difficulty": "0x020000",
        "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "author": "0x0000000000000000000000000000000000000000",
        "timestamp": "0x00",
        "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "extraData": "0x11bbe8db4e347b4e8c937c1c8370e4b5ed33adb3db69cbdb7a38e1e50b1b82fa",
        "gasLimit": "0x47E7C4"
    }
    
    self["accounts"] = {}

    for k,v in other:
        dotpos = k.find(".")            # allow 1-level nesting
        if dotpos >= 0:
            part1 = k[:dotpos]
            part2 = k[dotpos+1:]
            if part1 in self:
                self[part1] = {}
            self[part1][part2] = v
        else:
            self[k] = v
    return self

class Node:
    """Holds everything about node, can access it. But cannot run it."""    

    _counter = 0;

    def __init__(self, **kwargs):
        Node._counter = Node._counter + 1
        self.nodeName = kwargs.get('nodeName', "Node" + str(Node._counter))
        self.nodeID   = kwargs.get('nodeID', str(Node._counter))
        self.bindIP   = kwargs.get('bindIP', "127.0.0." + str(Node._counter))
        self.basePort = kwargs.get('basePort', 1231)
        self.sChain   = None
        self.config   = None
        self.running  = False
        self.eth      = None

class SChain:

    _counter = 0    

    def __init__(self, nodes, prefill=[], config=Config(), **kwargs):
        # TODO throw if len(prefill)>9
        # TODO throw if repeating node IDs
        SChain._counter = SChain._counter + 1
        self.sChainName = kwargs.get('sChainName', "Chain" + str(SChain._counter))
        self.sChainID   = kwargs.get('sChainID', SChain._counter)
        self.nodes = list(nodes)
        self.config = config            # TODO make a copy!?
#        for k,v in prefill.items():
#            self.config["accounts"][k] = {"balance":v}
        self.running = False
        self.eth = None

    def balance(acc):
        pass

    def nonce(acc):
        pass

    def code(acc):
        pass

    def transaction(**kwargs):
        pass

    def block():
        pass

    def start():
        pass

    def stop():
        pass

class LocalStarter:
    # TODO Implement monitoring of dead processes!

    def __init__(self, chain, exe, proxy):

        self.chain = chain
        self.exe   = exe
        self.dir = TemporaryDirectory()
        self.popens = []

        for n in self.chain.nodes:
            nodeDir = self.dir.name+"/"+n.nodeID
            os.makedirs(nodeDir)
            ipcDir  = nodeDir
            cfgFile = nodeDir+"/config.json"

            f = io.open(cfgFile, "w")
            json.dump(chain.config, f)
            f.close()

            # TODO Handle exceptions!
            self.popens.append(Popen([self.exe, "--no-discovery", "--config", cfgFile, "-d", nodeDir, "--ipcpath", ipcDir]))
        pass

    def start():
        pass
    def stop():
        pass
    def running():
        pass
