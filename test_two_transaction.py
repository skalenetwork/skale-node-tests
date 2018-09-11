from sktest import *
from sktest_helpers import *

def test_one_node():
    ch = createDefaultChain(numNodes = 1)
    ch.start()
    assert(ch.eth.blockNumber == 0)
    assert(ch.nonce(0) == 0)

    balance = ch.balance(0)
    ch.transaction()
    ch.transaction()
    
    assert(ch.eth.blockNumber == 2)
    assert(ch.nonce(0) == 2)
    assert(balance > ch.balance(0))

    ch.stop()

def test_two_nodes():
    ch = createDefaultChain(numNodes = 2)
    ch.start()
    assert(ch.eth.blockNumber == 0)
    assert(ch.nonce(0) == 0)

    ch.transaction()
    ch.transaction()

    assert(ch.compareAllStates() is None)

    ch.stop()

def test_three_nodes():
    ch = createDefaultChain(numNodes = 3)
    ch.start()
    assert(ch.eth.blockNumber == 0)
    assert(ch.nonce(0) == 0)

    ch.transaction()
    ch.transaction()

    assert(ch.compareAllStates() is None)

    ch.stop()

