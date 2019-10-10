from sktest import *
from sktest_helpers import *
from solc import compile_files
from web3.contract import *
import time
import json

ch = create_default_chain(num_nodes=int(os.getenv("NUM_NODES", 4)), num_accounts=2)
ch.start()

print("started")

compiled = compile_files(["Topic.sol"])
topic_sol = compiled['Topic.sol:Topic']

print("compiled")

try:

    Topic = ch.eth.contract(abi=topic_sol['abi'], bytecode=topic_sol['bin'])
    tx = Topic.constructor().buildTransaction({'from':ch.accounts[0]})

    hash = ch.transaction_async(data=tx['data'], to="0x0000000000000000000000000000000000000000", value=998, gas=300000)

    print("async")

    receipt = None
    while not receipt:
        receipt = ch.eth.getTransactionReceipt(hash)
        time.sleep(0.1)

    print(receipt)

    topic1 = ch.eth.contract(
        address=receipt.contractAddress,
        abi=topic_sol['abi'],
    )

    print(topic1)

    #print("Before:")
    #print( topic1.functions.get().call() )

    tx = topic1.functions.set('Contract Test Topic').buildTransaction({'from':ch.accounts[0]})

    hash = ch.transaction_async(data=tx['data'], gas=300000)

    receipt = None
    while not receipt:
        receipt = ch.eth.getTransactionReceipt(hash)
        time.sleep(0.1)

    print(receipt)

    print("After:")
    print( topic1.functions.get().call() )

except Exception as e:
    print("excepted!")
    print(str(e))
    input()

