from sktest_helpers import *
import pytest
import web3

nAcc  = 1000

@pytest.fixture
def schain():
    ch = create_custom_chain(num_nodes=1, num_accounts=nAcc+1, empty_blocks = False, rotate_after_block = 64)
    ch.start(start_timeout = 10)

    yield (ch)

    ch.stop()

def test_rotation(schain):
    ch = schain
    eth = ch.eth

    bytecode = "6080604052348015600f57600080fd5b50607d80601d6000396000f3fe60806040527f64696d616c6974000000000000000000000000000000000000000000000000004360001b6001430160001b6040518082815260200191505060405180910390a200fea264697066735822122011b1aa9b28bd72ec161cb5940c556f98779f86b02a6a258f7072186aefe0378d64736f6c63430006010033"
    abi = [
	    {
		    "stateMutability": "payable",
		    "type": "fallback"
	    }
    ]

    Logger = eth.contract(abi=abi, bytecode=bytecode)
    deploy_tx = Logger.constructor().buildTransaction()
    deploy_tx['from'] = ch.accounts[nAcc]       # 1 over last
    deploy_tx['nonce'] = eth.getTransactionCount(ch.accounts[nAcc])
    signed_deploy = w3.eth.account.signTransaction(deploy_tx, private_key=ch.privateKeys[nAcc])
    deploy_hash = eth.sendRawTransaction(signed_deploy.rawTransaction)
    receipt = eth.waitForTransactionReceipt(deploy_hash)

    contractAddress = receipt['contractAddress']

    block_no = 0
    def on_block():

        print('-------------------')

        b1 = 0
        b2 = block_no

        logs = eth.getLogs({
            'fromBlock'   : b1,
            'toBlock'     : b2,
            'address': contractAddress
        })

        next_to_find = block_no - 255
        if next_to_find < 2:
            next_to_find = 2        # 0 is genesis, 1 is contract creation
        for i in range(len(logs)):
            t1 = web3.Web3.toInt(logs[i]['topics'][0])
            print(t1, next_to_find)
            if t1 < next_to_find:
                continue
            assert(t1  == next_to_find)
            next_to_find += 1

        print('====================')

        b1 = block_no - 400
        b2 = block_no - 100

        if b1 >= 2:   # 0 is genesis, 1 is contract creation
            logs = eth.getLogs({
                'fromBlock'   : b1,
                'toBlock'     : b2,
                'address': contractAddress
            })

            next_to_find = block_no - 255
            for i in range(len(logs)):
                t1 = web3.Web3.toInt(logs[i]['topics'][0])
                print(t1, next_to_find)
                if t1 < next_to_find:
                    continue
                assert (t1 == next_to_find)
                next_to_find += 1

    prev_block_no = 0

    hash1 = eth.getBlock(1)['hash']

    i = 0
    while True:
        # create
        acc1 = i % nAcc
        nonce = i // nAcc
        t = ch.transaction_obj(value=1, _from=acc1, to=contractAddress, nonce=nonce, gas=99000)

        # send
        while(True):
            try:
                h = eth.sendRawTransaction(t)
                r = eth.waitForTransactionReceipt(h)
                block_no = eth.blockNumber
                on_block()
                break
            except Exception as e:
                if str(e).find('transaction nonce') == -1:
                	raise
                time.sleep(1)

        # just ask for some old block
        try:
            b1 = eth.getBlock(1)
        except Exception as ex:
            assert(str(ex).find('not found') != -1)
            b1 = None
        assert(b1 is None or b1['hash'] == hash1)

        # end this if block #300 has gone
        if block_no >= 300+256:
            try:
                eth.getBlock(300)
            except Exception as ex:
                assert(str(ex).find('not found') != -1)
                break

        i += 1
