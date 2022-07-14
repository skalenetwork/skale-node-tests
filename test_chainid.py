from sktest_helpers import *
import pytest

@pytest.fixture(scope="module", params=["0x11", "0x11223344", "0x112233445566", "0xd2baaecab8944", "0xfffffffffffff", "0xffffffffffffe"])
def schain_with_id(request):
    chain_id = request.param
    ch = create_chain_with_id(num_nodes=1, num_accounts=2, chain_id = chain_id)
    ch.start(start_timeout = 15)
    yield ch
    ch.stop()

def test_transaction_without_id(schain_with_id):
    ch = schain_with_id
    try:
        ch.transaction(chain_id = None)
        assert(False and "Transaction without chainID should fail")
    except:
        pass

def test_transaction_with_id(schain_with_id):
    ch = schain_with_id
    chain_id = ch.chainID
    ch.transaction(chain_id = chain_id)

def test_bad_transaction(schain_with_id):
    ch = schain_with_id
    chain_id = "0xdeadbeef"

    with pytest.raises(ValueError, match="signature"):
        ch.transaction(chain_id = chain_id)
