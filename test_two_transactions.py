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
    ch.transaction()
    
    assert(ch.eth.blockNumber == 2)
    assert(ch.nonce(0) == 2)
    assert(balance > ch.balance(0))

def test_N_nodes(schainN):
    ch = schainN
    assert(ch.eth.blockNumber == 0)
    assert(ch.nonce(0) == 0)

    ch.transaction()
    ch.transaction()

    assert(ch.compareAllStates() is None)


