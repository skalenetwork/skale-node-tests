from tempfile import TemporaryDirectory
import os
import io
import json
from subprocess import Popen, DEVNULL, PIPE, STDOUT, TimeoutExpired
import copy
import time
import binascii
import pickle
from threading import Timer
import web3
from web3.auto import w3
import signal
import types

w3.eth.enable_unaudited_features()

def patch_eth(eth):
    def pauseConsensus(eth, pause):
        eth._provider.make_request("debug_pauseConsensus", [pause])
    def pauseBroadcast(eth, pause):
        eth._provider.make_request("debug_pauseBroadcast", [pause])

    eth.pauseConsensus = types.MethodType(pauseConsensus, eth)
    eth.pauseBroadcast = types.MethodType(pauseBroadcast, eth)

def _transaction2json(eth, t, accounts):
#    print("_transaction2json", t)
    res = eth.getTransaction(t).__dict__
    accounts[res["from"]] = {}
    accounts[res["to"]]   = {}
    return res

def _block2json(eth, block, accounts):
    # print("_block2json", block['number'])
    block = block.__dict__

    transactions = {}
    for t in block["transactions"]:
        transactions[t.hex()] = _transaction2json(eth, t.hex(), accounts)
    block["transactions"] = transactions
    return block

def _node2json(eth):
    blocks = []
    accounts = {}
    block_number = eth.blockNumber
    for i in range(block_number + 1):
        blocks.append(_block2json(eth, eth.getBlock(i), accounts))
    #    i = 0
    #    for k in accounts:
    #        print("account:", i)
    #        accounts[k] = {
    #            "balance": eth.getBalance(k),
    #            "nonce"  : eth.getTransactionCount(k),
    #            "code"   : eth.getCode(k)
    #        }
    #        i+=1
    return {
        "blocks": blocks
        # "accounts": accounts
    }


def _iterate_dicts(a, b):
    """Return dict only with keys with difference. Or None if there is none."""

    difference = {}
    for k in a:
        if k not in b:
            difference[k] = (a[k], None)
        else:
            cmp = deep_compare(a[k], b[k])
            if cmp is not None:
                difference[k] = cmp
    for k in b:
        if k not in a:
            difference[k] = (None, b[k])
    if difference:
        return difference
    else:
        return None


def _iterate_lists(a, b):
    """Returns None for equal arrays,\
    else returns nulls in positions of equal elements, or their 'difference' if unequal"""

    difference = []
    different = False
    for a_element, b_element in zip(a, b):
        cmp = deep_compare(a_element, b_element)
        difference.append(cmp)
        if cmp is not None:
            different = True
    if len(a) > len(b):
        different = True
        for element in a[len(difference):]:
            difference.append((element, None))
    elif len(b) > len(a):
        different = True
        for element in b[len(difference):]:
            difference.append((None, element))
    if different:
        return difference
    else:
        return None

def deep_compare(a, b):
    """Returns None for equal objects,
    pair for unequal simple objects,
    tree with paths to unequal elements of array with nulls on place of equal elements"""

    if type(a) != type(b):
        return a, b
    elif (not type(a) is dict) and (not type(a) is list):
        if a == b:
            return None
        else:
            return a, b
    if type(a) is dict:
        return _iterate_dicts(a, b)
    else:
        return _iterate_lists(a, b)

def _compare_states(nodes):
    assert len(nodes) > 1
    res = []
    has_any = False
    # print("_node2json", "0")
    obj0 = _node2json(nodes[0].eth)
    for n in nodes:
        # print("_node2json", n.nodeID)
        obj = _node2json(n.eth)
        cmp = deep_compare(obj0, obj)
        res.append(cmp)
        if cmp is not None:
            has_any = True
    if has_any:
        return res
    else:
        return None


def _print_path(path):
    if path:
        return f'object{path}: '
    else:
        return ''


def list_differences(a, b, path=''):
    if type(a) != type(b):
        return [f'{_print_path(path)}values have different types']
    difference = []
    if type(a) is list:
        if len(a) != len(b):
            return [f'{_print_path(path)}lists have different lengths']
        for index, (value_a, value_b) in enumerate(zip(a, b)):
            difference += list_differences(value_a, value_b, f'{path}[{index}]')
    elif type(a) is dict:
        for key in a:
            if key not in b:
                difference += [f'{_print_path(path)}key {key} does not present in the second object']
            else:
                difference += list_differences(a[key], b[key], f'{path}[\'{key}\']')
        for key in b:
            if key not in a:
                difference += [f'{_print_path(path)}key {key} does not present in the first object']
    elif a != b:
        difference += [f'{_print_path(path)}{a} != {b}']
    return difference

# n[i].eth.getTransactionReceipt(hash)


def load_private_keys(path, password, count=0):
    # TODO Exceptions?!
    files = os.listdir(path)
    res = []
    i = 0
    for f in files:
        fd = open(path + "/" + f)
        key_encrypted = fd.read()
        fd.close()
        key_open = w3.eth.account.decrypt(key_encrypted, password)
        res.append(key_open)
        i += 1
        if count != 0 and i == count:
            break
    return res


def _wait_on_filter(eth_filter, dt):
    while True:
        e = eth_filter.get_new_entries()
        if len(e) > 0:
            return e
        time.sleep(dt)


def get_config(other=None):
    """Simple function that returns default config as a python dictionary
    and optionally appends it from the dictionary passed."""

    config = {
        "sealEngine": "Ethash",
        "params": {
            "accountStartNonce": "0x00",
            "homesteadForkBlock": "0x0",
            "daoHardforkBlock": "0x0",
            "EIP150ForkBlock": "0x0",
            "EIP155ForkBlock": "0x0",
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
        },
        "genesis": {
            "nonce": "0x0000000000000042",
            "difficulty": "0x020000",
            "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "author": "0x0000000000000000000000000000000000000000",
            "timestamp": "0x00",
            "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "extraData": "0x11bbe8db4e347b4e8c937c1c8370e4b5ed33adb3db69cbdb7a38e1e50b1b82fa",
            "gasLimit": "0x47E7C400"
        },
        "accounts": {}
    }

    if other is not None:
        for key, value in other.items():
            dot_position = key.find(".")  # allow 1-level nesting
            if dot_position >= 0:
                part1 = key[:dot_position]
                part2 = key[dot_position + 1:]
                if part1 not in config:
                    config[part1] = {}
                config[part1][part2] = value
            else:
                config[key] = value
    return config


class Node:
    """Holds everything about node, can access it. But cannot run it."""

    _counter = 0

    def __init__(self, **kwargs):
        Node._counter = Node._counter + 1
        self.nodeName = kwargs.get('nodeName', "Node" + str(Node._counter))
        self.nodeID = kwargs.get('nodeID', Node._counter)
        self.bindIP = kwargs.get('bindIP', "127.0.0." + str(Node._counter))
        self.basePort = kwargs.get('basePort', 1231)
        self.sChain = None
        self.config = None
        self.running = False
        self.eth = None
        self.ipcPath = None


class SChain:

    _counter = 0
    _pollInterval = 0.2

    def __init__(self, nodes, starter, prefill=None, config=get_config(), keys_file="./keys.all", keys_password="1234",
                 **kwargs):
        # TODO throw if len(prefill)>9
        # TODO throw if repeating node IDs
        SChain._counter = SChain._counter + 1
        self.sChainName = kwargs.get('schainName', "Chain" + str(SChain._counter))
        self.sChainID = kwargs.get('schainID', SChain._counter)
        self.nodes = list(nodes)
        self.config = copy.deepcopy(config)
        self.starter = starter
        self.running = False
        self.eth = None
        for n in self.nodes:
            assert n.sChain is None
            n.sChain = self
            n.config = self.config

        with open(keys_file, "rb") as fd:
            self.privateKeys = pickle.load(fd)
            assert (len(self.privateKeys) >= len(prefill))
            del self.privateKeys[len(prefill):]

        print("Loaded private keys")

        # TODO Make addresses.all customizable!
        try:
            with open("./addresses.all", "rb") as fd:
                self.accounts = pickle.load(fd)
            assert (len(self.accounts) >= len(prefill))
            del self.accounts[len(prefill):]
            if prefill is not None:
                for i in range(len(prefill)):
                    private_key = self.privateKeys[i]
                    balance = prefill[i]
                    address = self.accounts[i]
                    self.config["accounts"][address] = {"balance": str(balance)}
            print("Loaded public keys (addresses)")
        except Exception as ex:
            self.accounts = []
            if prefill is not None:
                for i in range(len(prefill)):
                    private_key = self.privateKeys[i]
                    balance = prefill[i]
                    address = w3.eth.account.privateKeyToAccount(private_key).address
                    self.accounts.append(address)
                    self.config["accounts"][address] = {"balance": str(balance)}

            with open("./addresses.all", "wb") as fd:
                pickle.dump(self.accounts, fd)

            print("Computed public keys (addresses)")

    def balance(self, i):
        return self.eth.getBalance(self.accounts[i])

    def nonce(self, i):
        return self.eth.getTransactionCount(self.accounts[i])

    def code(self, i):
        return self.eth.getCode(self.accounts[i])

    def all_filter(self, filter_name):
        ret = []
        for n in self.nodes:
            ret.append(n.eth.filter(filter_name))
        return ret

    @staticmethod
    def wait_all_filter(filters):
        ret = []
        for f in filters:
            ret.append(_wait_on_filter(f, SChain._pollInterval))
        return ret

    def transaction_obj(self, **kwargs):
        assert len(self.accounts) > 0
        _from = kwargs.get("_from", 0)
        to = kwargs.get("to", 1)
        value = kwargs.get("value", self.balance(_from) // 2)
        nonce = kwargs.get("nonce", self.nonce(_from))

        from_addr = self.accounts[_from]
        to_addr = self.accounts[to]

        transaction = {
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "gas": 21000,
            "gasPrice": 0,
            "nonce": nonce
        }
        signed = w3.eth.account.signTransaction(transaction, private_key=self.privateKeys[_from])
        return "0x" + binascii.hexlify(signed.rawTransaction).decode("utf-8")

    def transaction_async(self, **kwargs):
        tx = self.transaction_obj(**kwargs)
        return self.eth.sendRawTransaction(tx)

    def transaction(self, **kwargs):
        pending_filter = self.all_filter('pending')
        latest_filter = self.all_filter('latest')
        self.transaction_async(**kwargs)
        self.wait_all_filter(pending_filter)
        return self.wait_all_filter(latest_filter)

    def block(self):
        return self.transaction(value=0)

    def start(self):
        self.starter.start(self)

        #proxies = {'http': 'http://127.0.0.1:2234'};
        #, request_kwargs={'proxies': proxies}

        for n in self.nodes:
            provider = web3.Web3.HTTPProvider("http://" + n.bindIP + ":" + str(n.basePort + 3))
            n.eth = web3.Web3().eth
            n.eth._provider = provider
            patch_eth(n.eth)
        self.eth = self.nodes[0].eth
        self.running = True  # TODO Duplicates functionality in Starter!

    def stop(self):
        self.starter.stop()
        self.running = False

    def state(self, i):
        return _node2json(self.nodes[i].eth)

    def main_state(self):
        return self.state(0)

    def compare_all_states(self):
        return _compare_states(self.nodes)

    def __del__(self):
        self.stop()

def _make_config_node(node):
    return {
        "nodeName": node.nodeName,
        "nodeID"  : node.nodeID,
        "bindIP"  : node.bindIP,
        "basePort": node.basePort,
        "logLevel": "trace",
        "logLevelProposal": "trace",
        "emptyBlockIntervalSec": 3600
    }

def _make_config_schain_node(node, index):
    return {
        "nodeID"   : node.nodeID,
        "ip"       : node.bindIP,
        "basePort" : node.basePort,
        "schainIndex": index
    }


def _make_config_schain(chain):
    ret = {
        "schainName": chain.sChainName,
        "schainID"  : chain.sChainID,
        "nodes"     : []
    }
    for i in range(len(chain.nodes)):
        ret["nodes"].append(_make_config_schain_node(chain.nodes[i], i))
    return ret

class LocalStarter:
    # TODO Implement monitoring of dead processes!
    chain = None
    started = False

    def __init__(self, exe, proxy):
        self.exe = exe
        self.proxy = proxy
        self.dir = TemporaryDirectory()
        self.exe_popens = []
        self.proxy_popens = []
        self.running = False

    def start(self, chain):
        assert not self.started
        self.started = True
        self.chain = chain

        for_delayed_proxies = []

        # TODO Handle exceptions!
        for n in self.chain.nodes:
            assert not n.running

            node_dir = self.dir.name + "/" + str(n.nodeID)
#            node_dir = "dir/" + str(n.nodeID)
            ipc_dir = node_dir
            os.makedirs(node_dir)
            cfg_file = node_dir + "/config.json"

            cfg = copy.deepcopy(chain.config)
            cfg["skaleConfig"] = {
                "nodeInfo": _make_config_node(n),
                "sChain": _make_config_schain(self.chain)
            }
            f = io.open(cfg_file, "w")
            #            f = io.open("/home/dimalit/config.js", "w")
            json.dump(cfg, f, indent=1)
            n.config = cfg
            f.close()

            # TODO Close all of it?
            aleth_out = io.open(node_dir + "/" + "aleth.out", "w")
            aleth_err = io.open(node_dir + "/" + "aleth.err", "w")
            proxy_out = io.open(node_dir + "/" + "proxy.out", "w")
            proxy_err = io.open(node_dir + "/" + "proxy.err", "w")

            self.exe_popens.append(
                Popen([#"/usr/bin/strace", '-o'+node_dir+'/aleth.trace',
                       self.exe,
                       "--no-discovery",
                       "--config", cfg_file,
                       "-d", node_dir,
                       "--ipcpath", ipc_dir,
                       "-v", "4"],
                      stdout=aleth_out,
                      stderr=aleth_err,
                      env = {"DATA_DIR":node_dir}
                ))
            # HACK +0 +1 +2 are used by consensus
            url = f"http://{n.bindIP}:{n.basePort + 3}"

            for_delayed_proxies.append({'args': [self.proxy, ipc_dir + "/geth.ipc", url],
                                        'stdout': proxy_out, 'stderr': proxy_err})

            n.ipcPath = ipc_dir + "/geth.ipc"
            n.running = True

        #input('Press enter when nodes start')

        def signal_handler(signum, frame):
            raise Exception("Timed out!")

        signal.signal(signal.SIGALRM, signal_handler)
        TIMEOUT=30
        signal.alarm(TIMEOUT)
        try:
            input('Press enter when nodes start')
            print('thank you')
            signal.alarm(0)
        except Exception as ex:
            if str(ex) == "Timed out!":
                print("\ntimed out")
            else:
                print("something awful happened!" + repr(ex))
                signal.alarm(0)
                time.sleep(TIMEOUT)
            #Exception("Timed out!")




#        for p in for_delayed_proxies:
#            self.proxy_popens.append( Popen(p['args'], stdout = p['stdout'], stderr = p['stderr']) )

#        print('Wait for json rpc proxies start')
#        time.sleep(2)

        self.running = True

    def stop(self):
        assert hasattr(self, "chain")

        # TODO race conditions?
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
        self.dir.cleanup()

def ssh_exec(address, command):
    ssh = Popen( [ "ssh", address ], stdin=PIPE, stdout=PIPE, stderr=STDOUT, bufsize=1 )    # line-buffered

    try:
        comm = ssh.communicate(command.encode(), timeout=1)
        print(comm[0].decode())
    except TimeoutExpired:
        pass

class RemoteStarter:
    # TODO Implement monitoring of dead processes!
    chain = None
    started = False

    # condif is array of hashes: {address, dir, exe}
    def __init__(self, ssh_config):
        self.ssh_config = copy.deepcopy(ssh_config)
        self.running = False

    def start(self, chain):
        assert not self.started
        assert len(self.ssh_config) == len(chain.nodes)
        self.started = True
        self.chain = chain

        # TODO Handle exceptions!
        for i in range(len(self.chain.nodes)):
            n = self.chain.nodes[i]
            ssh_conf = self.ssh_config[i]

            assert not n.running

            node_dir = ssh_conf["dir"]
            cfg_file = node_dir + "/config.json"

            command = ""
            command += "mkdir -p "+node_dir
            command += "; cd " + node_dir

            cfg = copy.deepcopy(chain.config)
            cfg["skaleConfig"] = {
                "nodeInfo": _make_config_node(n),
                "sChain": _make_config_schain(self.chain)
            }
            json_str = json.dumps(cfg)
            n.config = cfg

            command += "; echo '" + json_str + "' >" + cfg_file

            command += ("; bash -c \"DATA_DIR="+node_dir+" nohup " +
                       ssh_conf["exe"] +
                       " --no-discovery" +
                       " --config " + cfg_file +
                       " -d " + node_dir + 
                       " -v " + "4" + "\" 2>nohup.err >nohup.out&")
            command += "\nexit\n"

            ssh_exec(ssh_conf['address'], command)

            n.running = True

        self.running = True

    def stop(self):
        assert hasattr(self, "chain")

        # TODO race conditions?
        for n in self.chain.nodes:
            n.running = False
        self.running = False

class NoStarter:
    chain = None

    def __init__(self):
        self.running = False

    def start(self, chain):
        assert self.chain is None

        self.chain = chain
        for n in self.chain.nodes:
            assert not n.running
            n.running = True
        self.running = True

    def stop(self):
        assert self.chain is not None

        for n in self.chain.nodes:
            n.running = False
        self.running = False

