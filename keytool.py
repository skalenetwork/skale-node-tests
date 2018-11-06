import web3
from web3.auto import w3

from sktest_helpers import load_private_keys

import sys
import pickle
from tempfile import TemporaryDirectory
from subprocess import Popen
import time

w3.eth.enable_unaudited_features()

def usage():
    print("USAGE:")
    print("python keytool.py generate|decrypt <aleth_path>|<source_path> [<dest_path>] <n>")
    sys.exit()

def decrypt(source_path, dest_path, n = 0):
    keys = load_private_keys(source_path, '1234', n)
    fd = open(dest_path, "wb")
    pickle.dump(keys, fd)
    fd.close()

def generate(aleth_path, n):
    tmp = TemporaryDirectory().name
    popen = Popen([aleth_path, "--no-discovery", "-d", tmp, "--ipcpath", tmp, "-v", "4"])
    time.sleep(2)

    personal = web3.Web3(web3.Web3.IPCProvider(tmp+"/geth.ipc")).personal
    for i in range(n):
        personal.newAccount("1234")

    popen.terminate()
    popen.wait()
    print("Go get your keys in ~/.web3/keys")

try:
    if sys.argv[1] == "decrypt":
        source_path = sys.argv[2]
        dest_path   = sys.argv[3]
        n           = 0

        if len(sys.argv) >= 5:
            n = int(sys.argv[4])

        decrypt(source_path, dest_path, n)

    elif sys.argv[1] == "generate":
        aleth_path = sys.argv[2]
        n = int(sys.argv[3])

        generate(aleth_path, n)

    else:
        usage()

    print("OK")

except IndexError as ex:
    usage()

