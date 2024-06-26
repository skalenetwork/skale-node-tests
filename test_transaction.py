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

    assert (ch.eth.blockNumber == 1)
    assert (ch.nonce(0) == 1)
    assert (balance > ch.balance(0))


def test_two_nodes(schain2):
    ch = schain2

    eth2 = ch.nodes[1].eth
    acc1 = ch.accounts[0]
    acc2 = ch.accounts[1]
    balance1 = eth2.getBalance(acc1)
    balance2 = eth2.getBalance(acc2)

    assert (eth2.blockNumber == 0)
    assert (eth2.getTransactionCount(acc1) == 0)

    ch.transaction()

    assert (eth2.blockNumber == 1)
    assert (eth2.getTransactionCount(acc1) == 1)
    assert (balance1 > eth2.getBalance(acc1))
    assert (balance2 < eth2.getBalance(acc2))
    # gas cost goes to 0 address
    assert (balance1 + balance2 == eth2.getBalance(acc1) + eth2.getBalance(acc2) + eth2.getBalance("0x0000000000000000000000000000000000000000"))

    assert (ch.compare_all_states() is None)


def test_n_nodes(schain_n):
    ch = schain_n
    assert (ch.eth.blockNumber == 0)
    assert (ch.nonce(0) == 0)

    ch.transaction()

    assert (ch.compare_all_states() is None)
