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
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired

import docker
import web3
from docker.types import LogConfig
from web3.auto import w3

from config import merge as config_merge, to_string as config_to_string

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

    eth.pauseConsensus = types.MethodType(pauseConsensus, eth)
    eth.pauseBroadcast = types.MethodType(pauseBroadcast, eth)
    eth.forceBlock = types.MethodType(forceBlock, eth)
    eth.forceBroadcast = types.MethodType(forceBroadcast, eth)
    eth.debugInterfaceCall = types.MethodType(debugInterfaceCall, eth)


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


def getLatestSnapshotBlockNumber(eth):
    res = eth._provider.make_request("skale_getLatestSnapshotBlockNumber", [])
    return res["result"]


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

    _dkg_id = 0

    _nodes_bls_key_name = ['BLS_KEY:SCHAIN_ID:1:NODE_ID:0:DKG_ID:'+str(_dkg_id),
                           'BLS_KEY:SCHAIN_ID:1:NODE_ID:1:DKG_ID:'+str(_dkg_id),
                           'BLS_KEY:SCHAIN_ID:1:NODE_ID:2:DKG_ID:'+str(_dkg_id),
                           'BLS_KEY:SCHAIN_ID:1:NODE_ID:3:DKG_ID:'+str(_dkg_id)
                           ]

    _nodes_bls_public_key = [['21863114478776400949858605566548714783346181193496545440390567475652443827860',
                              '10464107885494525519581620200197214454081423744513061107893525107639603306406',
                              '21184166360997189515339842524276751085701691914330721286626083200868381851507',
                              '9691275586475923350239965219458214853398053456671458906602512073155412477765'],
                             ['3009259274536749924291167728223211541338185496216243046746034399509040584590',
                              '13289581877516010176096865600363954975544318150612132009900978273590840827671',
                              '3509060907621479358705196470121888970981082575252325352540589302112883506131',
                              '9623845779864445397658552419482290886596710265287763759908787602461317591522'],
                             ['8742968334342026931671975134702795911399825106438585936076894251874910472349',
                              '4256915126029311077517288250609053798571789913766130193692320276924121794604',
                              '14455184817129501171111955486792313997711359251214278761532423502769296099702',
                              '20678269015896935775387749530686987901502683463963862941654962217268957250896'],
                             ['21167588835499686017105978704419960201196471486209839086008146103138932244571',
                              '5805323932014273847465702979165147225542511837196532508389683490529742871954',
                              '21053346572510464338712665283936249079516915662009476660014987681112849530309',
                              '20041358704535665129364549031054869404767444547260082485437106537062214376293']
                            ]

    _nodes_public_key = ['2ac99031b5c438a5c2514a3085d524039ace523d96f77a2ec457d57a169ee55aff43cf65c3ceaa8cd207c6202bc82960d9a131fc5bec9da5abf4cbaa6183c622',
                             '74f987105ea5a3ef07dbb7fd658fcc691480ff9688c9802b7646949a082372f85f1e791d510114ec9d15e82f102d43afa4a576143099c8707e73b34ea475a9db',
                             '216821816e5c457656ec2662ffaff1c83037145db04162aee0f36e0e9239f5429b62e0c2905688deb20598af00ab8ade0404d7cc4bea40836f0086e4b9abe60a',
                             '99396f3d8bcc5964bcf1da0cbf82ed8b56cffe4a1aa83e281eee4b18b00ff16604586c541637e508d9f27752257d34ca4b32b24a10e43195d4b414d8bf9b3c02']
                             
    _ecdsa_keys = ['NEK:db4e5d0b510dcc55e8353986f1cb7aa5d3ae29511ca71ec5d4f211228607d2c3',
                   'NEK:dd5202917d25aa6d9df272f5150be3e6b86729d8e3dfe4289342d6e14c273c28',
                   'NEK:a5dbdb349b68eeab9baffa336b47f36bc10b0692857aa331b57a79b1adfa3c85',
                   'NEK:283fb163fa64e9c92d9e6820a4c92fe25ae22cb04f56c3ee233a8b1620c1ded1']
                               
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
        self.rotateAfterBlock = kwargs.get('rotateAfterBlock', -1)
        # self.snapshotInterval = kwargs.get('snapshotInterval', -1)
        self.snapshottedStartSeconds = kwargs.get(
            'snapshottedStartSeconds', -1
        )
        self.keyShareName = Node._nodes_bls_key_name[Node._counter - 1]
        self.insecureBLSPublicKey0 = Node._nodes_bls_public_key[Node._counter - 1][0]
        self.insecureBLSPublicKey1 = Node._nodes_bls_public_key[Node._counter - 1][1]
        self.insecureBLSPublicKey2 = Node._nodes_bls_public_key[Node._counter - 1][2]
        self.insecureBLSPublicKey3 = Node._nodes_bls_public_key[Node._counter - 1][3]
        self.publicKey = Node._nodes_public_key[Node._counter - 1]
        self.ecdsaKeyName = Node._ecdsa_keys[Node._counter - 1]

class SChain:

    _counter = 0
    _pollInterval = 0.2

    def __init__(self, nodes, starter, prefill=None,
                 keys_file="./keys.all", keys_password="1234",
                 **kwargs):
        # TODO throw if len(prefill)>9
        # TODO throw if repeating node IDs
        SChain._counter = SChain._counter + 1
        self.sChainName = kwargs.get('schainName',
                                     "Chain" + str(SChain._counter))
        self.sChainID = kwargs.get('schainID', SChain._counter)
        self.emptyBlockIntervalMs = kwargs.get('emptyBlockIntervalMs', -1)
        self.snapshotIntervalMs = kwargs.get('snapshotIntervalMs', -1)
        self.nodes = list(nodes)
        self.chainID = kwargs.get('chainID', "0x1")
        self.config_addons = {"params": {"chainID": self.chainID}, "accounts": {}}
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
        value = kwargs.get("value", self.balance(_from) // 2)
        nonce = kwargs.get("nonce", self.nonce(_from))
        data = kwargs.get("data", "0x")
        gas = int(kwargs.get("gas", 21000))
        chainId = kwargs.get("chain_id", None)

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
            "gasPrice": 1000,
            "nonce": nonce,
            "data": data,
            "chainId": chainId
        }
        if "code" in kwargs:
            transaction["code"] = kwargs["code"]

        signed = w3.eth.account.signTransaction(
            transaction,
            private_key=self.privateKeys[_from]
        )
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

    def wait_block(self):
        latest_filter = self.all_filter('latest')
        return self.wait_all_filter(latest_filter)

    def start(self, **kwargs):
        self.starter.start(self, **kwargs)

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

    def __del__(self):
        self.stop()


def _make_config_node(node):
    return {
        "nodeName": node.nodeName,
        "nodeID": node.nodeID,
        "bindIP": node.bindIP,
        "basePort": node.basePort,
        "logLevel": "trace",
        "logLevelConfig": "trace",
        "rotateAfterBlock": node.rotateAfterBlock,
        "enable-debug-behavior-apis": True,
        "ecdsaKeyName": node.ecdsaKeyName,
        "wallets": {
            "ima": {
                "url": "https://45.76.37.95:1026",
                "keyShareName": node.keyShareName,
                "t": 3,
                "n": 4,
                "BLSPublicKey0": node.insecureBLSPublicKey0,
                "BLSPublicKey1": node.insecureBLSPublicKey1,
                "BLSPublicKey2": node.insecureBLSPublicKey2,
                "BLSPublicKey3": node.insecureBLSPublicKey3,
                "commonBLSPublicKey0": "6755929213917339040852441844310046252748896713668544376639154919014308133767",
                "commonBLSPublicKey1": "16212816063676187554897571363811397516383815123546603244301177987699598362330",
                "commonBLSPublicKey2": "6361189426596797545844743213974188186637149612868715455753070595839250503891",
                "commonBLSPublicKey3": "19287282379061921102666373161822860515914623644484094304962106762868478741554"
            }
        }
        # "catchupIntervalMs": 1000000000
    }


def _make_config_schain_node(node, index):
    return {
        "nodeID": node.nodeID,
        "ip": node.bindIP,
        "basePort": node.basePort,
        "schainIndex": index + 1,
        "blsPublicKey0": node.insecureBLSPublicKey0,
        "blsPublicKey1": node.insecureBLSPublicKey1,
        "blsPublicKey2": node.insecureBLSPublicKey2,
        "blsPublicKey3": node.insecureBLSPublicKey3,
        "publicKey": node.publicKey
    }


def _make_config_schain(chain):
    ret = {
        "schainName": chain.sChainName,
        "schainID": chain.sChainID,
        "nodes": [],
        "emptyBlockIntervalMs": chain.emptyBlockIntervalMs,
        "snapshotIntervalMs": chain.snapshotIntervalMs,
        # "schainOwner": chain.accounts[0],
        "storageLimit": 1000*1000*1000*1000
    }
    for i in range(len(chain.nodes)):
        ret["nodes"].append(_make_config_schain_node(chain.nodes[i], i))
    return ret


class LocalDockerStarter:
    chain = None
    started = False

    DEFAULT_IMAGE = 'skalenetwork/schain:1.46-develop.14'

    def __init__(self, image=None, config = None):
        self.image = image or LocalDockerStarter.DEFAULT_IMAGE
        self.dir = TemporaryDirectory()
        self.running = False
        self.client = docker.client.from_env()
        self.containers = []
        self.volumes = []
        if config == None:
            with open("config0.json", "r") as f:
                config = json.load(f)
        self.config = copy.deepcopy(config)
    def create_volume(self, volume_name):
        self.volumes.append(
            self.client.volumes.create(
                name=volume_name, driver='lvmpy',
                driver_opts={})
        )

    def run_container(self, name, node_dir, data_dir_volume_name,
                      env, cmd, **kwargs):
        self.containers.append(
           self.client.containers.run(
               image=self.image, name=name,
               detach=True,
               network='host',
               command=cmd,
               volumes={
                   data_dir_volume_name: {
                       'bind': '/data_dir', 'mode': 'rw'
                   },
                   node_dir: {
                       'bind': '/skale_node_data', 'mode': 'rw'
                   }
               },
               environment=env,
               **kwargs,
           ))

    def compose_cmd(self, node):
        cmd = ' '.join([
                "--ws-port", str(node.basePort + 2),
                "--http-port", str(node.basePort + 3),
                "--aa", "always",
                "--config", '/skale_node_data/config.json',
                "-d", '/data_dir/',
                "-v", "4",
                "--web3-trace",
                "--acceptors", "1"
            ])
        if node.snapshottedStartSeconds > -1:
            url = 'http://{}:{}'.format(
                self.chain.nodes[0].bindIP,
                self.chain.nodes[0].basePort + 3
            )
            cmd += f' --download-snapshot {url}'
            time.sleep(node.snapshottedStartSeconds)
        return cmd

    def compose_env_options(self, node):
        return {
            **os.environ,
            'HTTP_RPC_PORT': self.chain.nodes[node.nodeID - 1].basePort + 3,
            'WS_RPC_PORT': self.chain.nodes[node.nodeID - 1].basePort + 2,
            'HTTPS_RPC_PORT': self.chain.nodes[node.nodeID - 1].basePort + 7,
            'WSS_RPC_PORT': self.chain.nodes[node.nodeID - 1].basePort + 8,
            'DATA_DIR': '/data_dir/',
            'CONFIG_FILE': '/skale_node_data/config.json',
            'LEAK_EXPIRE': '20',
            'LEAK_PID_CHECK': '1',
        }

    @classmethod
    def compose_docker_options(cls):
        return {
          "security_opt": [
            "seccomp=unconfined"
          ],
          "restart_policy": {
            "MaximumRetryCount": 10,
            "Name": "on-failure"
          },
          "cap_add": [
              "SYS_PTRACE", "SYS_ADMIN"
          ],
          "log_config": LogConfig(
              type=LogConfig.types.JSON,
              config={"max-size": "250m", "max-file": "5"}),
        }

    def make_config(self, node, chain):
        cfg = copy.deepcopy(self.config)
        config_merge(cfg, chain.config_addons)
        cfg["skaleConfig"] = {
            "nodeInfo": _make_config_node(node),
            "sChain": _make_config_schain(self.chain)
        }
        return cfg

    @classmethod
    def save_config(cls, config, node_dir):
        os.makedirs(node_dir, exist_ok=True)
        cfg_filepath = node_dir + "/config.json"
        with open(cfg_filepath, 'w') as cfg_file:
            json.dump(config, cfg_file, indent=1)

    def create_schain_node(self, chain, node):
        assert not node.running

        data_dir_volume_name = f'data-dir{node.nodeID}'
        self.create_volume(data_dir_volume_name)

        node_dir = os.path.join(os.getenv('DATA_DIR', self.dir.name), str(node.nodeID))

        node.config = self.make_config(node, chain)
        LocalDockerStarter.save_config(node.config, node_dir)

        ipc_dir = node_dir
        node.ipcPath = ipc_dir + "/geth.ipc"

        docker_options = LocalDockerStarter.compose_docker_options()
        env = self.compose_env_options(node)
        cmd = self.compose_cmd(node)

        container_name = f'schain-node{node.nodeID}'
        self.run_container(container_name, node_dir,
                           data_dir_volume_name, env, cmd, **docker_options)
        node.running = True

    def start(self, chain, start_timeout=100):
        assert not self.started
        self.started = True
        self.chain = chain
        for node in self.chain.nodes:
            assert not node.running
            # TODO Handle exceptions!
            self.create_schain_node(chain, node)

        assert len(self.client.volumes.list()) == len(self.chain.nodes)
        assert len(self.client.containers.list()) == len(self.chain.nodes)
        safe_input_with_timeout('Press enter when nodes start', start_timeout)
        self.running = True
    
    def start_after_stop(self, chain, start_timeout=100):
        self.start(chain, start_timeout)

    def destroy_containers(self):
        for c in self.containers:
            try:
                c.remove(force=True)
            except docker.errors.NotFound:
                continue
        print('Containers removed')

    def destroy_volumes(self):
        for v in self.volumes:
            try:
                v.remove(force=True)
            except docker.errors.NotFound:
                continue
        print('Volumes removed')

    def stop(self):
        assert hasattr(self, "chain")
        self.destroy_containers()
        self.destroy_volumes()
        self.running = False
        self.dir.cleanup()
    
    def stop_without_cleanup(self):
        assert hasattr(self, "chain")
        self.destroy_containers()
        self.destroy_volumes()
        self.running = False

    def stop_node(self, pos):
        if not self.chain.nodes[pos].running:
            return
        self.containers[pos].stop(timeout=10)
        self.chain.nodes[pos].running = False

    def wait_node_stop(self, pos):
        if not self.chain.nodes[pos].running:
            return
        self.containers[pos].wait(timeout=60)
        self.chain.nodes[pos].running = False

    def node_exited(self, pos):
        return self.containers[pos].status == 'exited'


class LocalStarter:
    # TODO Implement monitoring of dead processes!
    chain = None
    started = False

    def __init__(self, exe, config=None):
        self.exe = exe
        self.dir = TemporaryDirectory()
        if config == None:
            with open("config0.json", "r") as f:
                config = json.load(f)
        self.config = copy.deepcopy(config)
        self.exe_popens = []
        self.running = False

    def start(self, chain, start_timeout=40):
        assert not self.started
        self.started = True
        self.chain = chain

        # TODO Handle exceptions!
        for n in self.chain.nodes:
            assert not n.running

            node_dir = os.path.join(os.getenv('DATA_DIR', self.dir.name), str(n.nodeID))
            ipc_dir = node_dir
            os.makedirs(node_dir)
            cfg_file = node_dir + "/config.json"

            cfg = copy.deepcopy(self.config)
            config_merge(cfg, self.chain.config_addons)
            cfg["skaleConfig"] = {
                "nodeInfo": _make_config_node(n),
                "sChain": _make_config_schain(self.chain)
            }
            f = io.open(cfg_file, "w")
            json.dump(cfg, f, indent=1)
            n.config = cfg
            f.close()

            # TODO Close all of it?
            aleth_out = io.open(node_dir + "/" + "aleth.out", "w")
            aleth_err = io.open(node_dir + "/" + "aleth.err", "w")

            env = os.environ.copy()

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
                popen_args.append("--public-key")
                popen_args.append("11087880408379223720179864713155560103154798592635045798293882410743651570446:3564106700478864553326232013660949455083826448005354972026557092863213195493:11447019497857856092493405784790665626780763256081713143842436936251732746449:1772291325702049391502102464643150908631803508034733810722819621406995840280")
                time.sleep(n.snapshottedStartSeconds)

            popen = Popen(
                popen_args,
                stdout=aleth_out,
                stderr=aleth_err,
                env=env
            )

            n.pid = popen.pid
            n.args = popen_args
            n.stdout = aleth_out
            n.stderr = aleth_err
            n.env = env

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
    
    def restart_node(self, pos):
        assert self.started
        n = self.chain.nodes[pos]
        assert n.running

        self.stop_node(pos)
        self.wait_node_stop(pos)

        popen = Popen(
            n.args,
            stdout=n.stdout,
            stderr=n.stderr,
            env=n.env
        )

        n.pid = popen.pid
        self.exe_popens[pos] = popen
        n.running = True
    
    def start_after_stop(self, chain, start_timeout=40):
        assert not self.started
        self.started = True
        self.chain = chain

        # TODO Handle exceptions!
        for n in self.chain.nodes:
            assert not n.running

            node_dir = os.path.join(os.getenv('DATA_DIR', self.dir.name), str(n.nodeID))
            ipc_dir = node_dir
            cfg_file = node_dir + "/config.json"

            cfg = copy.deepcopy(self.config)
            config_merge(cfg, self.chain.config_addons)
            cfg["skaleConfig"] = {
                "nodeInfo": _make_config_node(n),
                "sChain": _make_config_schain(self.chain)
            }
            f = io.open(cfg_file, "w")
            json.dump(cfg, f, indent=1)
            n.config = cfg
            f.close()

            # TODO Close all of it?
            aleth_out = io.open(node_dir + "/" + "aleth.out", "w")
            aleth_err = io.open(node_dir + "/" + "aleth.err", "w")

            env = os.environ.copy()

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
                env=env
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

        for pos in range(len(self.chain.nodes)):
            self.stop_node(pos)

        for pos in range(len(self.chain.nodes)):
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
            p.terminate()

    # TODO race conditions?
    def wait_node_stop(self, pos):
        p = self.exe_popens[pos]
        if p and p.poll() is None:
            p.wait()
            self.exe_popens[pos] = None

    def node_exited(self, pos):
        return self.exe_popens[pos].poll() is not None


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
    def __init__(self, ssh_config, config = None):
        self.ssh_config = copy.deepcopy(ssh_config)
        if config == None:
            with open("config0.json", "r") as f:
                config = json.load(f)
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
    def __init__(self, ssh_config, config=None):
        self.ssh_config = copy.deepcopy(ssh_config)
        if config == None:
            with open("config0.json", "r") as f:
                config = json.load(f)
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
