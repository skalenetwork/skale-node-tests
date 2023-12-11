import binascii
import copy
import json
import io
import os
import glob
import pickle
import signal
import shutil
import time
import types

from tempfile import TemporaryDirectory
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired, run

#import docker
import web3
#from docker.types import LogConfig
from web3.auto import w3

from config_tools.config import merge as config_merge, to_string as config_to_string

# w3.eth.enable_unaudited_features()

def safe_input_with_timeout(s, timeout):
    if timeout == 0:
        print("Zero wait")
        return

    def signal_handler(signum, frame):
        raise Exception("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(timeout)
    try:
        input(s)
        signal.alarm(0)
    except Exception as ex:
        if str(ex) == "Timed out!":
            print("\ntimed out")
        else:
            print("nowhere to input from: " + repr(ex))
            signal.alarm(0)
            time.sleep(timeout)
        # Exception("Timed out!")

def patch_eth(eth):
    def pauseConsensus(eth, pause):
        eth._provider.make_request("debug_pauseConsensus", [pause])

    def pauseBroadcast(eth, pause):
        eth._provider.make_request("debug_pauseBroadcast", [pause])

    def forceBlock(eth):
        eth._provider.make_request("debug_forceBlock", [])

    def forceBroadcast(eth, h):
        eth._provider.make_request("debug_forceBroadcast", [h])

    def debugInterfaceCall(eth, arg):
        res = eth._provider.make_request("debug_interfaceCall", [arg])
        return res["result"]
        
    def getLatestSnapshotBlockNumber(eth):
        res = eth._provider.make_request("skale_getLatestSnapshotBlockNumber", [])
        res = res["result"]
        if res == "earliest":
            res = 0
        else:
            res = int(res)
        return res
    
    def getSnapshotSignature(eth, bn):
        res = eth._provider.make_request("skale_getSnapshotSignature", [bn])
        if res.get("error", ""):
            return res["error"]["message"]
        return res["result"]

    def getSnapshot(eth, block_number):
        res = eth._provider.make_request("skale_getSnapshot", {"blockNumber":block_number})
        if res.get("error", ""):
            return res["error"]["message"]
        res = res['result']
        if res.get('error', ''):
            return res['error']
        return res

    def downloadSnapshotFragment(eth, _from, size, is_binary=False):
        res = eth._provider.make_request("skale_downloadSnapshotFragment", {"from":_from,"isBinary":is_binary,"size":size})
        return res["result"]

    def setSchainExitTime(eth, finishTime):
        res = eth._provider.make_request("setSchainExitTime", {'finishTime':finishTime})
        if res.get("error", ""):
            return res["error"]["message"]
    
    def getGenesisState(eth):
        res = eth._provider.make_request("skale_getGenesisState", {})
        if res.get("error", ""):
            return res["error"]["message"]
        res = res['result']
        if res.get('error', ''):
            return res['error']
        return res

    eth.pauseConsensus = types.MethodType(pauseConsensus, eth)
    eth.pauseBroadcast = types.MethodType(pauseBroadcast, eth)
    eth.forceBlock = types.MethodType(forceBlock, eth)
    eth.forceBroadcast = types.MethodType(forceBroadcast, eth)
    eth.debugInterfaceCall = types.MethodType(debugInterfaceCall, eth)
    eth.getLatestSnapshotBlockNumber = types.MethodType(getLatestSnapshotBlockNumber, eth)
    eth.getSnapshotSignature = types.MethodType(getSnapshotSignature, eth)
    eth.getSnapshot = types.MethodType(getSnapshot, eth)
    eth.downloadSnapshotFragment = types.MethodType(downloadSnapshotFragment, eth)
    eth.setSchainExitTime = types.MethodType(setSchainExitTime, eth)

def _transaction2json(eth, t, accounts):
    # print("_transaction2json", t)
    res = eth.getTransaction(t).__dict__
    accounts[res["from"]] = {}
    accounts[res["to"]] = {}
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
    """Returns None for equal arrays,
    else returns nulls in positions of equal elements,
    or their 'difference' if unequal"""

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
    """Returns None for equal objects, pair for unequal simple objects,
    tree with paths to unequal elements of array with nulls
    on place of equal elements"""

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
            difference += list_differences(
                value_a, value_b, f'{path}[{index}]'
            )
    elif type(a) is dict:
        for key in a:
            if key not in b:
                difference += [f'{_print_path(path)}key {key} does not present in the second object']  # noqa
            else:
                difference += list_differences(a[key], b[key],
                                               f'{path}[\'{key}\']')
        for key in b:
            if key not in a:
                difference += [f'{_print_path(path)}key {key} does not present in the first object']  # noqa
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

class Node:
    """Holds everything about node, can access it. But cannot run it."""

    _counter = 0

    def __init__(self, **kwargs):
        Node._counter = Node._counter + 1
        self.nodeName = kwargs.get('nodeName', "Node" + str(Node._counter))
        self.nodeID = kwargs.get('nodeID', Node._counter)
        self.bindIP = kwargs.get('bindIP', "127.0.0." + str(Node._counter))
        self.basePort = kwargs.get('basePort', 1231)
        self.wsPort = kwargs.get('wsPort', 7000+Node._counter)
        self.sChain = None
        self.config = None
        self.running = False
        self.eth = None
        self.ipcPath = None
        # self.snapshotInterval = kwargs.get('snapshotInterval', -1)
        self.snapshottedStartSeconds = kwargs.get(
            'snapshottedStartSeconds', -1
        )
        self.requireSnapshotMajority = kwargs.get('requireSnapshotMajority', True)
        self.downloadGenesisState = kwargs.get('downloadGenesisState', True)
        self.historic = kwargs.get('historic', False)
        self.sync = kwargs.get('sync', False)

class SChain:

    _counter = 0
    _pollInterval = 0.2

    def __init__(self, nodes, starter, prefill=None,
                 keys_file="./keys.all", keys_password="1234",
                 **kwargs):
        # TODO throw if len(prefill)>9
        # TODO throw if repeating node IDs
        SChain._counter = SChain._counter + 1
        self.sChainName = kwargs.get('schainName') or "Chain" + str(SChain._counter)
        self.sChainID = kwargs.get('schainID') or SChain._counter
        self.emptyBlockIntervalMs = kwargs.get('emptyBlockIntervalMs') or -1
        self.snapshotIntervalSec = kwargs.get('snapshotIntervalSec') or -1
        self.snapshotDownloadTimeout = kwargs.get('snapshotDownloadTimeout') or 60
        self.snapshotDownloadInactiveTimeout = kwargs.get('snapshotDownloadInactiveTimeout') or 60
        self.nodes = list(nodes)
        self.chainID = kwargs.get('chainID') or "0x1"
        self.dbStorageLimit = kwargs.get('dbStorageLimit') or 120*1024*1024
        self.bls = kwargs.get('bls', False) or False
        self.mtm = kwargs.get('mtm', False) or False
        self.config_addons = {
            "params": {"chainID": self.chainID},
            "accounts": {},
            "skaleConfig": {
                "sChain": {
                    "emptyBlockIntervalMs": self.emptyBlockIntervalMs,
                    "snapshotIntervalSec": self.snapshotIntervalSec,
                    "snapshotDownloadTimeout": self.snapshotDownloadTimeout,
                    "snapshotDownloadInactiveTimeout": self.snapshotDownloadInactiveTimeout,
                    "dbStorageLimit": self.dbStorageLimit,
                    "multiTransactionMode": self.mtm
                }
            }
        }
        self.starter = starter
        self.running = False
        self.eth = None
        for n in self.nodes:
            assert n.sChain is None, n.sChain
            n.sChain = self

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
                    self.config_addons["accounts"][address] = {
                        "balance": str(balance)
                    }
            print("Loaded public keys (addresses)")
        except Exception:
            self.accounts = []
            if prefill is not None:
                for i in range(len(prefill)):
                    private_key = self.privateKeys[i]
                    balance = prefill[i]
                    address = w3.eth.account.privateKeyToAccount(
                        private_key).address
                    self.accounts.append(address)
                    self.config_addons["accounts"][address] = {
                        "balance": str(balance)
                    }

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
        value = kwargs.get("value", 1000 * 1000 * 1000 * 1000 * 1000)
        nonce = kwargs.get("nonce", self.nonce(_from))
        data = kwargs.get("data", "0x")
        gas = int(kwargs.get("gas", 21000))
        chainId = kwargs.get("chain_id", self.chainID)

        from_addr = self.accounts[_from]
        if type(to) is str:
            to_addr = to
        else:
            to_addr = self.accounts[to]

        transaction = {
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "gas": gas,
            "gasPrice": 1000000,
            "nonce": nonce,
            "data": data,
            "chainId": chainId
        }
        if "code" in kwargs:
            transaction["code"] = kwargs["code"]

        signed = w3.eth.account.sign_transaction(
            transaction,
            private_key=self.privateKeys[_from]
        )
        return "0x" + binascii.hexlify(signed.rawTransaction).decode("utf-8")

    def transaction_async(self, **kwargs):
        tx = self.transaction_obj(**kwargs)
        return self.eth.sendRawTransaction(tx)

    def transaction(self, **kwargs):
        # pending_filter = self.all_filter('pending')
        latest_filter = self.all_filter('latest')
        self.transaction_async(**kwargs)
        # self.wait_all_filter(pending_filter)
        return self.wait_all_filter(latest_filter)

    def block(self):
        return self.transaction(value=0)

    def wait_block(self):
        latest_filter = self.all_filter('latest')
        return self.wait_all_filter(latest_filter)

    def start(self, **kwargs):
        self.starter.start(self, **kwargs)

        # proxies = {'http': 'http://127.0.0.1:2234'};
        # , request_kwargs={'proxies': proxies}

        for n in self.nodes:
            provider = web3.Web3.HTTPProvider(
                "http://" + n.bindIP + ":" + str(n.basePort + 3),
                request_kwargs = {'timeout': 20})
            n.eth = web3.Web3(provider).eth
            n.eth._provider = provider
            patch_eth(n.eth)
        self.eth = self.nodes[0].eth
        self.running = True  # TODO Duplicates functionality in Starter!
    
    def start_after_stop(self, **kwargs):
        self.starter.start_after_stop(self, **kwargs)

        # proxies = {'http': 'http://127.0.0.1:2234'};
        # , request_kwargs={'proxies': proxies}

        for n in self.nodes:
            provider = web3.Web3.HTTPProvider(
                "http://" + n.bindIP + ":" + str(n.basePort + 3))
            n.eth = web3.Web3(provider).eth
            n.eth._provider = provider
            patch_eth(n.eth)
        self.eth = self.nodes[0].eth
        self.running = True  # TODO Duplicates functionality in Starter!

    def wait_start(self):
        while True:
            try:
                self.eth.blockNumber
                break
            except Exception:
                time.sleep(1)

    def stop(self):
        self.starter.stop()
        self.running = False

    def stop_without_cleanup(self):
        self.starter.stop_without_cleanup()
        self.running = False

    def stop_node(self, pos):
        self.starter.stop_node(pos)

    def wait_node_stop(self, pos):
        self.starter.wait_node_stop(pos)

    def node_exited(self, pos):
        return self.starter.node_exited(pos)

    def state(self, i):
        return _node2json(self.nodes[i].eth)

    def main_state(self):
        return self.state(0)

    def compare_all_states(self):
        return _compare_states(self.nodes)
    
    def prepare_to_restore(self, latest_snapshot):
        self.starter.prepare_to_restore(latest_snapshot)

    def __del__(self):
        self.stop()

class LocalStarter:
    # TODO Implement monitoring of dead processes!
    chain = None
    started = False

    def __init__(self, exe, config={}):
        self.exe = exe
        self.dir = TemporaryDirectory()
        #if config == None:
        #    with open("config0.json", "r") as f:
        #        config = json.load(f)
        self.config = copy.deepcopy(config)
        self.exe_popens = []
        self.running = False

    def start(self, chain, start_timeout=40, restart_option=False, shared_space_path=""):
        assert not self.started
        self.started = True
        self.chain = chain

        cfg = copy.deepcopy(self.config)
        config_merge(cfg, self.chain.config_addons)
            
        with open(os.path.join(self.dir.name, "config0.json"), "w") as f:
            json.dump(cfg, f, indent = 1)
            
        ip_ports = [str(node.bindIP)+":"+str(node.basePort) for node in self.chain.nodes if not node.sync and not node.historic]

        have_sync = any(n.sync for n in self.chain.nodes)
        if have_sync:
            sync_ip_port = [str(node.bindIP)+":"+str(node.basePort) for node in self.chain.nodes if node.sync][0]
        have_historic = any(n.historic for n in self.chain.nodes)
        if have_historic:
            historic_ip_port = [str(node.bindIP)+":"+str(node.basePort) for node in self.chain.nodes if node.historic][0]

        simple_nodes_count = len(self.chain.nodes)-have_sync-have_historic

        if self.chain.bls:
            os.environ["SGX_URL"] = "https://167.235.155.228:1026";
        os.system("./config_tools/make_configs.sh "
                  +str(simple_nodes_count)+" "+",".join(ip_ports)+" "
                  +os.path.join(self.dir.name, "config0.json") + " "
                  +(f"--historic {historic_ip_port}" if have_historic else "") + " "
                  +(f"--sync {sync_ip_port}" if have_sync else "") + " "
                 )

        # give numbers to sync and historic configs
        if have_sync:
            os.rename("config-sync.json", f"config{simple_nodes_count+have_sync}.json");
        if have_historic:
            os.rename("config-historic.json", f"config{simple_nodes_count+have_sync+have_historic}.json");

        # TODO Handle exceptions!
        idx = 0
        for n in self.chain.nodes:
            assert not n.running
            idx+=1

            node_dir = os.path.join(os.getenv('DATA_DIR', self.dir.name), str(idx))
            ipc_dir = node_dir
            try:
                os.makedirs(node_dir)
            except:
                pass
            cfg_file = node_dir + "/config.json"

            # add address field to nodeGroups section in config if bls is enabled
            if self.chain.bls:
                config_json = None
                with open("./config"+str(idx)+".json") as f:
                    config_json = json.load(f)
                new_config = config_json
                for _, node_info in config_json['skaleConfig']['sChain']['nodeGroups']['0']['nodes'].items():
                    pk_str = node_info[2][2:]
                    address = web3.Web3.keccak(hexstr=pk_str).hex()
                    address = "0x" + address[26:]
                    node_info.append( address )
                #write updated config on disk
                json_dump = json.dumps(new_config, indent=4)
                with open("./config"+str(idx)+".json", "w+") as outfile:
                    outfile.write(json_dump)

            ##!n.config = cfg
            shutil.move("./config"+str(idx)+".json", cfg_file)

            # TODO Close all of it?
            aleth_out = io.open(node_dir + "/" + "aleth.out", "w")
            aleth_err = io.open(node_dir + "/" + "aleth.err", "w")

            env = os.environ.copy()
            env['DATA_DIR'] = node_dir
            env["NO_ULIMIT_CHECK"] = "1"

            popen_args = [
                # "/usr/bin/strace", '-o'+node_dir+'/aleth.trace',
                #"stdbuf", "-oL",
                # "heaptrack",
                # "valgrind", "--tool=callgrind", #"--separate-threads=yes",
                self.exe,
                "--http-port", str(n.basePort + 3),
#                "--ws-port", str(n.wsPort),
                "--aa", "always",
                "--config", cfg_file,
                "-d", node_dir,
                # "--ipcpath", ipc_dir,		# ACHTUNG!!! 107 characters max!!
                "-v", "4",
                "--web3-trace",
                "--acceptors", "1",
                "--main-net-url", "http://127.0.0.1:1111"
            ]

            try:
              if os.environ["SGX_URL"] and not n.sync and not n.historic:
                  popen_args.append("--sgx-url")
                  popen_args.append(os.environ["SGX_URL"])
            except:
              pass

            if n.snapshottedStartSeconds > -1:
                popen_args.append("--download-snapshot")
                popen_args.append("http://" + self.chain.nodes[0].bindIP + ":" + str(self.chain.nodes[0].basePort + 3))  # noqa
                # HACK send transactions to have different snapshot hashes!
                n1 = self.chain.nodes[0]
                provider = web3.Web3.HTTPProvider(
                "http://" + n1.bindIP + ":" + str(n1.basePort + 3),
                request_kwargs = {'timeout': 20})
                chain.eth = web3.Web3(provider).eth
                for i in range(n.snapshottedStartSeconds):
                    try:
                        print("transaction")
                        chain.transaction_async()
                        print("ok")
                    except Exception as ex:
                        print(str(ex))
                        pass    # already exists
                    time.sleep(1)

            if not n.requireSnapshotMajority:
                popen_args.append('--no-snapshot-majority')
                popen_args.append(self.chain.nodes[0].bindIP)

            if not n.downloadGenesisState:
                popen_args.append('--download-genesis-state')

            if shared_space_path != "":
                popen_args.append('--shared-space-path')
                popen_args.append(shared_space_path)

            popen = Popen(
                popen_args,
                stdout=aleth_out,
                stderr=aleth_err,
                env=env,
                preexec_fn=os.setsid
            )

            n.pid = popen.pid
            n.args = popen_args
            n.stdout = aleth_out
            n.stderr = aleth_err
            n.env = env
            n.data_dir = node_dir

            self.exe_popens.append(popen)
            # HACK +0 +1 +2 are used by consensus
            # url = f"http://{n.bindIP}:{n.basePort + 3}"

            # n.ipcPath = ipc_dir + "/geth.ipc"
            n.running = True

        safe_input_with_timeout('Press enter when nodes start', start_timeout)

#        for p in for_delayed_proxies:
#            self.proxy_popens.append(
#                Popen(p['args'], stdout = p['stdout'], stderr = p['stderr'])
#            )

#        print('Wait for json rpc proxies start')
#        time.sleep(2)

        self.running = True

    def cpulimit(self, pos, limit):
        n = self.chain.nodes[pos]
        os.system(f"cpulimit -p {n.pid} -l {limit} -b")

    def restart_node(self, pos, args, delay_sec = 0):
        assert self.started
        n = self.chain.nodes[pos]
        assert n.running

        self.stop_node(pos)
        self.wait_node_stop(pos)

        for _ in range(delay_sec):
            try:
                self.chain.transaction_async()
            except Exception as ex:
                print(str(ex))
            time.sleep(1)

        self.start_node_after_stop(pos, args)
    
    def start_after_stop(self, chain, start_timeout=40):
        assert not self.started
        self.started = True
        self.chain = chain

        # TODO Handle exceptions!
        idx = 0
        for n in self.chain.nodes:
            assert not n.running
            idx+=1

            node_dir = os.path.join(os.getenv('DATA_DIR', self.dir.name), str(n.nodeID))
            ipc_dir = node_dir
            cfg_file = node_dir + "/config.json"

            shutil.move("./config"+str(idx)+".json", cfg_file)

            # TODO Close all of it?
            aleth_out = io.open(node_dir + "/" + "aleth.out", "w")
            aleth_err = io.open(node_dir + "/" + "aleth.err", "w")

            env = os.environ.copy()
            env['DATA_DIR'] = node_dir

            popen_args = [
                # "/usr/bin/strace", '-o'+node_dir+'/aleth.trace',
                # "stdbuf", "-oL",
                # "heaptrack",
                self.exe,
                "--http-port", str(n.basePort + 3),
                "--ws-port", str(n.wsPort),
                "--aa", "always",
                "--config", cfg_file,
                "-d", node_dir,
                # "--ipcpath", ipc_dir,		# ACHTUNG!!! 107 characters max!!
                "-v", "4",
                "--web3-trace",
                "--acceptors", "1"
            ]

            if n.snapshottedStartSeconds > -1:
                popen_args.append("--download-snapshot")
                popen_args.append("http://" + self.chain.nodes[0].bindIP + ":" + str(self.chain.nodes[0].basePort + 3))  # noqa
                time.sleep(n.snapshottedStartSeconds)

            popen = Popen(
                popen_args,
                stdout=aleth_out,
                stderr=aleth_err,
                env=env,
                preexec_fn=os.setsid
            )

            n.pid = popen.pid

            self.exe_popens.append(popen)
            # HACK +0 +1 +2 are used by consensus
            # url = f"http://{n.bindIP}:{n.basePort + 3}"

            # n.ipcPath = ipc_dir + "/geth.ipc"
            n.running = True

        safe_input_with_timeout('Press enter when nodes start', start_timeout)

#        for p in for_delayed_proxies:
#            self.proxy_popens.append(
#                Popen(p['args'], stdout = p['stdout'], stderr = p['stderr'])
#            )

#        print('Wait for json rpc proxies start')
#        time.sleep(2)

        self.running = True

    def stop(self):
        assert hasattr(self, "chain")
        if not self.running:
            return

        for pos in range(len(self.chain.nodes)):
            try:
                shutil.copyfile(self.dir.name+"/"+str(pos+1)+"/aleth.out", f"/tmp/{pos+1}.log")
                shutil.copyfile(self.dir.name+"/"+str(pos+1)+"/aleth.err", f"/tmp/{pos+1}_err.log")
            except:
                pass
            self.stop_node(pos)
            self.wait_node_stop(pos)

        self.running = False
        self.dir.cleanup()

    def stop_without_cleanup(self):
        assert hasattr(self, "chain")

        for pos in range(len(self.chain.nodes)):
            self.stop_node(pos)

        for pos in range(len(self.chain.nodes)):
            self.wait_node_stop(pos)

        self.running = False
        self.started = False
        self.exe_popens.clear()

    # TODO race conditions?
    def stop_node(self, pos):
        if not self.chain.nodes[pos].running:
            return
        self.chain.nodes[pos].running = False
        p = self.exe_popens[pos]
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)

    # TODO race conditions?
    def wait_node_stop(self, pos):
        p = self.exe_popens[pos]
        if p and p.poll() is None:
            p.wait()
            self.exe_popens[pos] = None

    def node_exited(self, pos):
        return self.exe_popens[pos].poll() is not None

    def node_exit_code(self, pos):
        return self.exe_popens[pos].poll()

    def start_node_after_stop(self, pos, args=[]):
        n = self.chain.nodes[pos]
        popen = Popen(
            n.args + args,
            stdout=n.stdout,
            stderr=n.stderr,
            env=n.env,
            preexec_fn=os.setsid
        )

        n.pid = popen.pid
        self.exe_popens[pos] = popen
        n.running = True

    def prepare_to_restore(self, latest_snapshot):
        for n in self.chain.nodes:
            d = os.path.join(os.getenv('DATA_DIR', self.dir.name), str(n.nodeID), "snapshots")
            snapshots_to_remove = [os.path.join(d, o) for o in os.listdir(d)
                        if os.path.isdir(os.path.join(d,o)) and o != str(latest_snapshot)]
            for snapshot in snapshots_to_remove:
                clean_data_dir = run(["btrfs", "subvolume", "delete", snapshot + "/a5cf2af8"])
                clean_data_dir = run(["btrfs", "subvolume", "delete", snapshot + "/filestorage"])
                clean_data_dir = run(["btrfs", "subvolume", "delete", snapshot + "/blocks_" + str(n.nodeID) + ".db"])
                clean_data_dir = run(["btrfs", "subvolume", "delete", snapshot + "/prices_" + str(n.nodeID) + ".db"])
                shutil.rmtree(snapshot)
            clean_data_dir = run(["btrfs", "subvolume", "delete", d + "/../" + "a5cf2af8"])
            clean_data_dir = run(["btrfs", "subvolume", "delete", d + "/../" + "filestorage"])
            clean_data_dir = run(["btrfs", "subvolume", "delete", d + "/../" + "blocks_" + str(n.nodeID) + ".db"])
            clean_data_dir = run(["btrfs", "subvolume", "delete", d + "/../" + "prices_" + str(n.nodeID) + ".db"])
            fileList = glob.glob(d + "/../" + "*.db")
            for file in fileList:
                shutil.rmtree(file)
            latest_snapshot_dir = os.path.join(d, str(latest_snapshot))
            new_snapshot_voulems = run(["btrfs", "subvolume", "snapshot", latest_snapshot_dir + "/a5cf2af8", d + "/.."])
            new_snapshot_voulems = run(["btrfs", "subvolume", "snapshot", latest_snapshot_dir + "/filestorage", d + "/.."])
            new_snapshot_voulems = run(["btrfs", "subvolume", "snapshot", latest_snapshot_dir + "/blocks_" + str(n.nodeID) + ".db", d + "/.."])
            new_snapshot_voulems = run(["btrfs", "subvolume", "snapshot", latest_snapshot_dir + "/prices_" + str(n.nodeID) + ".db", d + "/.."])


def ssh_exec(address, command):
    ssh = Popen(["ssh", address], stdin=PIPE, stdout=PIPE,
                stderr=STDOUT, bufsize=1)    # line-buffered

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
    def __init__(self, ssh_config, config = {}):
        self.ssh_config = copy.deepcopy(ssh_config)
        #if config == None:
        #    with open("config0.json", "r") as f:
        #        config = json.load(f)
        self.config = copy.deepcopy(config)
        self.running = False

    def start(self, chain):
        assert not self.started
        assert len(self.ssh_config) == len(chain.nodes)
        self.started = True
        self.chain = chain

        cfg = copy.deepcopy(self.config)
        config_merge(cfg, self.chain.config_addons)
        with open(os.path.join(self.dir.name, "config0.json"), "w") as f:
            json.dump(cfg, f, indent = 1)
            
        ip_ports = [str(node.bindIP)+":"+str(node.basePort) for node in self.chain.nodes]
            
        os.system("./config_tools/make_configs.sh "
                  +str(len(self.chain.nodes))+" "+",".join(ip_ports)+" "
                  +os.path.join(self.dir.name, "config0.json")
                 )

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

            json_str=""
            with open("./config"+str(i+1)+".json") as f:
                json_str = f.readLines()
                n.config = json.loads(json_str)

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
    
    def stop_without_cleanup(self):
        self.stop()


class RemoteDockerStarter:
    # TODO Implement monitoring of dead processes!
    chain = None
    started = False

    # config is array of hashes: {address, dir, exe}
    def __init__(self, ssh_config, config={}):
        self.ssh_config = copy.deepcopy(ssh_config)
        #if config == None:
        #    with open("config0.json", "r") as f:
        #        config = json.load(f)
        self.config = copy.deepcopy(config)
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

            cfg = copy.deepcopy(self.config)
            config_merge(cfg, self.chain.config_addons)
            cfg["skaleConfig"] = {
                "nodeInfo": _make_config_node(n),
                "sChain": _make_config_schain(self.chain)
            }
            json_str = json.dumps(cfg)
            n.config = cfg

            command += "; echo '" + json_str + "' >" + cfg_file

            command += ("; bash -c \" nohup " +
                        "docker run -d " +
                        #  " -e CONFIG_FILE=" + cfg_file +
                        #  " -d $DATA_DIR \
                        #  " --ipcpath $DATA_DIR \
                        #  " --http-port $HTTP_RPC_PORT \
                        #  " --https-port $HTTPS_RPC_PORT \
                        #  " --ws-port $WS_RPC_PORT \
                        #  " --wss-port $WSS_RPC_PORT \
                        #  " --ssl-key $SSL_KEY_PATH \
                        #  " --ssl-cert $SSL_CERT_PATH \
                        #  " -v 4  \
                        #  " --web3-trace \
                        #  " --enable-debug-behavior-apis \
                        #  " --aa no $DOWNLOAD_SNAPSHOT_OPTION

                        " -v " + node_dir + ":/schain_data" +
                        " -e DATA_DIR=/schain_data" +
                        " -e CONFIG_FILE=" + cfg_file +
                        "\" 2>nohup.err >nohup.out&")
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
    
    def stop_without_cleanup(self):
        self.stop()


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
    
    def stop_without_cleanup(self):
        self.stop()

class ManualStarter:

    def __init__(self, config = {}):
        self.chain = None
        self.config = copy.deepcopy( config )
        self.running = False

    def start(self, chain, start_timeout = None):
        assert self.chain is None

        self.chain = chain
        config = copy.deepcopy( self.config )
        config_merge( config, self.chain.config_addons)
        print(config_to_string(config))
        
        for n in self.chain.nodes:
            assert not n.running
            n.running = True
        self.running = True

    def stop(self):
        assert self.chain is not None

        for n in self.chain.nodes:
            n.running = False
        self.running = False
    
    def stop_without_cleanup(self):
        self.stop()
