from sktest_helpers import *
import pytest


@pytest.fixture
def schain1():
    ch = create_default_chain(num_nodes=1)
    ch.start()
    yield ch
    ch.stop()


@pytest.fixture
def schain2():
    ch = create_default_chain(num_nodes=2)
    ch.start()
    yield ch
    ch.stop()


@pytest.fixture(params=[2, 3])
def schain_n(request):
    ch = create_default_chain(num_nodes=request.param)
    ch.start()
    yield ch
    ch.stop()


def test_one_node(schain1):
    ch = schain1
    assert (ch.eth.blockNumber == 0)
    assert (ch.nonce(0) == 0)

    balance = ch.balance(0)
    ch.transaction()
    ch.transaction()

    assert (ch.eth.blockNumber == 2)
    assert (ch.nonce(0) == 2)
    assert (balance > ch.balance(0))


def test_n_nodes(schain_n):
    ch = schain_n
    assert (ch.eth.blockNumber == 0)
    assert (ch.nonce(0) == 0)

    ch.transaction()
    ch.transaction()

    assert (ch.compare_all_states() is None)
