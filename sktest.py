from tempfile import TemporaryDirectory
import os
import io
import json
from subprocess import Popen, DEVNULL
import copy
import time
import binascii

import web3
from web3.auto import w3

def _transaction2json(eth, t, accounts):
    res = eth.getTransaction(t).__dict__
    accounts[res["from"]] = {}
    accounts[res["to"]]   = {}
    return res

def _block2json(eth, block, accounts):
    block = block.__dict__
    
    transactions = {}
    for t in block["transactions"]:
        transactions[t.hex()] = _transaction2json(eth, t.hex(), accounts)
    block["transactions"] = transactions
    return block

def _node2json(eth):
    blocks = []
    accounts = {}
    blockNumber = eth.blockNumber
    for i in range(blockNumber):
        blocks.append(_block2json(eth, eth.getBlock(i), accounts))
    for k in accounts:
        accounts[k] = {
            "balance": eth.getBalance(k),
            "nonce"  : eth.getTransactionCount(k),
            "code"   : eth.getCode(k)
        }
    return {
        "blocks": blocks,
        "accounts": accounts
    }

def _iterate_dicts(a,b):
    """Return dict only with keys with difference. Or None if there is none."""

    ret = {}
    for k in a:
        if not k in b:
            ret[k] = (a[k], None)
        else:
            cmp = deep_compare(a[k], b[k])
            if not cmp is None:
                ret[k] = cmp
    for k in b:
        if k in a:
            continue
        else:
            ret[k] = (None, b[k])
    if len(ret)==0:
        return None
    else:
        return ret

def _iterate_lists(a,b):
    """Returns None for equal arrays, else returns nulls in positions of equal elements, or their 'difference' if unequal"""

    ret = []
    has_any = False
    for i in range(min(len(a), len(b))):
        cmp = deep_compare(a[i], b[i])
        ret.append(cmp)
        if cmp:
            has_any = True
    if len(a) > len(b):
        has_any = True
        for i in range(len(ret), len(a)):
            ret[i] = (a[i], None)
    elif len(b) > len(a):
        has_any = True    
        for i in range(len(ret), len(b)):
            ret[i] = (None, b[i])
    if has_any:
        return ret
    else:
        return None

def deep_compare(a, b):
    """Returns None for equal objects, pair for unequal simple objects, tree with paths to unequal elemetns of array with nulls on place of equal elements"""

    if type(a) != type(b):
        return (a,b)
    elif (not type(a) is dict) and (not type(a) is list):
        if a==b:
            return None
        else:
            return (a,b)
    if type(a) is dict:
       return _iterate_dicts(a, b)
    else:
        return _iterate_lists(a, b)
        
def _compare_states(nodes):
    assert len(nodes) > 1
    res = []
    obj0 = _node2json(nodes[0].eth)
    for n in nodes:
        obj = _node2json(n.eth)
        res.append(deep_compare(obj0, obj))
    return res
    
# n[i].eth.getTransactionReceipt(hash)

def loadPrivateKeys(path, password):
    #TODO Exceptions?!
    files = os.listdir(path)
    res = []
    for f in files:
        fd = open(path+"/"+f)
        key_crypted = fd.read()
        fd.close()
        key_open = w3.eth.account.decrypt(key_crypted, password)
        res.append(key_open)
    return res

def _waitOnFilter(filter, dt):
    e = []
    while True:
        e = filter.get_new_entries()
        if len(e) > 0:
            assert len(e) == 1
            return e[0]
        time.sleep(dt)

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
            if not part1 in self:
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
        self.nodeID   = kwargs.get('nodeID', Node._counter)
        self.bindIP   = kwargs.get('bindIP', "127.0.0." + str(Node._counter))
        self.basePort = kwargs.get('basePort', 1231)
        self.sChain   = None
        self.config   = None
        self.running  = False
        self.eth      = None
        self.pendingFilter = None
        self.latestFilter  = None

class SChain:

    _counter = 0
    _pollInterval = 0.2

    def __init__(self, nodes, starter, prefill=[], config=Config(), keysPath="./keys", keysPassword="1234", **kwargs):
        # TODO throw if len(prefill)>9
        # TODO throw if repeating node IDs
        SChain._counter = SChain._counter + 1
        self.sChainName = kwargs.get('schainName', "Chain" + str(SChain._counter))
        self.sChainID   = kwargs.get('schainID', SChain._counter)
        self.nodes = list(nodes)
        self.config = copy.deepcopy(config)
        self.starter = starter
        self.running = False
        self.eth = None
        for n in self.nodes:
            assert n.sChain is None
            n.sChain = self
            
        self.privateKeys = loadPrivateKeys(keysPath, keysPassword)
        self.accounts = []
        for i in range(len(prefill)):
            k = self.privateKeys[i]
            v = prefill[i]
            addr = w3.eth.account.privateKeyToAccount(k).address
            self.accounts.append(addr)
            self.config["accounts"][addr] = {"balance":v}

    def balance(self, i):
        return self.eth.getBalance(self.accounts[i])

    def nonce(self, i):
        return self.eth.getTransactionCount(self.accounts[i])

    def code(self, i):
        return self.eth.getCode(self.accounts[i])
        
    def _waitAllPending(self):
        ret = []
        for n in self.nodes:
            ret.append( _waitOnFilter(n.pendingFilter, SChain._pollInterval) )
        return ret

    def _waitAllLatest(self):
        ret = []
        for n in self.nodes:
            ret.append( _waitOnFilter(n.latestFilter, SChain._pollInterval) )
        return ret

    def transaction(self, **kwargs):
        assert len(self.accounts) > 0
        _from = kwargs.get("from", 0)
        to    = kwargs.get("to", 1)
        value = kwargs.get("value", self.balance(_from)//2)
        nonce = kwargs.get("nonce", self.nonce(_from))

        from_addr  = self.accounts[_from]
        to_addr    = self.accounts[to]
        
        transaction = {
            "from" : from_addr,
            "to"   : to_addr,
            "value": value,
            "gas"  : 21000,
            "gasPrice": 0,
            "nonce": nonce
        }
        signed = w3.eth.account.signTransaction(transaction, private_key=self.privateKeys[_from])
        hash   = self.eth.sendRawTransaction( "0x"+binascii.hexlify(signed.rawTransaction).decode("utf-8") )
        self._waitAllPending()
        return self._waitAllLatest()

    def block(self):
        return self.transaction(value=0)

    def start(self):
        self.starter.start(self)
        for n in self.nodes:
            n.eth = web3.Web3(web3.Web3.HTTPProvider("http://"+n.bindIP+":"+str(n.basePort+3))).eth
            n.pendingFilter = n.eth.filter('pending')
            n.latestFilter = n.eth.filter('latest')
        self.eth = self.nodes[0].eth
        self.running = True         # TODO Duplicates functionality in Starter!

    def stop(self):
        self.starter.stop()
        self.running = False
        
    def compareAll(self):
        return _compare_states(self.nodes)

def _makeConfigNode(node):
    return {
        "nodeName": node.nodeName,
        "nodeID"  : node.nodeID,
        "bindIP"  : node.bindIP,
        "basePort": node.basePort
    }
    
def _makeConfigSChainNode(node, index):
    return {
        "nodeID"   : node.nodeID,
        "ip"       : node.bindIP,
        "basePort" : node.basePort,
        "schainIndex": index
    }

def _makeConfigSChain(chain):
    ret = {
        "schainName": chain.sChainName,
        "schainID"  : chain.sChainID,
        "nodes"     : []
    }
    for i in range(len(chain.nodes)):
        ret["nodes"].append(_makeConfigSChainNode(chain.nodes[i], i))
    return ret
        
class LocalStarter:
    # TODO Implement monitoring of dead processes!

    def __init__(self, exe, proxy):
        self.exe   = exe
        self.proxy = proxy
        self.dir = TemporaryDirectory()
        self.exe_popens = []
        self.proxy_popens = []        
        self.running = False

    def start(self, chain):
        assert not hasattr(self, "chain")
        self.chain = chain
        # TODO Handle exceptions!
        for n in self.chain.nodes:
            assert not n.running
        
            nodeDir = self.dir.name+"/"+str(n.nodeID)
            ipcDir = nodeDir
            os.makedirs(nodeDir)
            cfgFile = nodeDir+"/config.json"

            cfg = copy.deepcopy(chain.config)
            cfg["skaleConfig"] = {
                "nodeInfo": _makeConfigNode(n),
                "sChain": _makeConfigSChain(self.chain)
            }
            f = io.open(cfgFile, "w")
            json.dump(cfg, f, indent=1)
            n.config = cfg
            f.close()

            self.exe_popens.append(Popen([self.exe, "--no-discovery", "--config", cfgFile, "-d", nodeDir, "--ipcpath", ipcDir]))
            time.sleep(2)
            # HACK +0 +1 +2 are used by consensus
            self.proxy_popens.append(Popen([self.proxy, ipcDir+"/geth.ipc", "http://"+n.bindIP+":"+str(n.basePort+3)], stdout=DEVNULL, stderr=DEVNULL))
            time.sleep(1)
            n.running = True
        self.running = True
        
    def stop(self):
        assert hasattr(self, "chain")
        
        #TODO race conditions?
        for n in self.chain.nodes:
            n.running = False
        for p in self.proxy_popens:
            if p.poll() is None:
                p.terminate()
                p.wait()    
        for p in self.exe_popens:
            if p.poll() is None:
                p.terminate()
                p.wait()
        self.running = False

