from sktest import *
from sktest_helpers import *
import pytest

@pytest.fixture
def schain1():
    ch = createDefaultChain(numNodes = 1)
    ch.start()
    yield ch
    ch.stop()

@pytest.fixture
def schain2():
    ch = createDefaultChain(numNodes = 2)
    ch.start()
    yield ch
    ch.stop()

@pytest.fixture(params=[2,3])
def schainN(request):
    ch = createDefaultChain(numNodes = request.param)
    ch.start()
    yield ch
    ch.stop()

def test_one_node(schain1):
    ch = schain1

    assert(ch.eth.blockNumber == 0)
    assert(ch.nonce(0) == 0)

    balance = ch.balance(0)
    ch.transaction()
    
    assert(ch.eth.blockNumber == 1)
    assert(ch.nonce(0) == 1)
    assert(balance > ch.balance(0))

def test_two_nodes(schain2):
    ch = schain2

    eth2 = ch.nodes[1].eth
    acc1 = ch.accounts[0]
    acc2 = ch.accounts[1]
    balance1 = eth2.getBalance(acc1)
    balance2 = eth2.getBalance(acc2)

    assert(eth2.blockNumber == 0)
    assert(eth2.getTransactionCount(acc1) == 0)

    ch.transaction()

    assert(eth2.blockNumber == 1)
    assert(eth2.getTransactionCount(acc1) == 1)
    assert(balance1 > eth2.getBalance(acc1))
    assert(balance1+balance2 == eth2.getBalance(acc1)+eth2.getBalance(acc2))

    assert(ch.compareAllStates() is None)

def test_N_nodes(schainN):
    ch = schainN
    assert(ch.eth.blockNumber == 0)
    assert(ch.nonce(0) == 0)

    ch.transaction()

    assert(ch.compareAllStates() is None)

