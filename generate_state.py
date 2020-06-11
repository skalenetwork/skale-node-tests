from sktest import *
from sktest_helpers import *
import time
import sys

global storage_size
storage_size = int(sys.argv[1])

ch = create_default_chain(num_nodes=1, num_accounts=2)
ch.start()

eth = ch.nodes[0].eth

bytecode = "608060405234801561001057600080fd5b5061017f806100206000396000f3fe60806040526004361061003f576000357c010000000000000000000000000000000000000000000000000000000090048063b9e95382146100dc57610040565b5b600034905060008090505b818163ffffffff1610156100d85780604051602001808263ffffffff1663ffffffff167c0100000000000000000000000000000000000000000000000000000000028152600401915050604051602081830303815290604052805190602001206000808363ffffffff1663ffffffff1681526020019081526020016000208190555080600101905061004b565b5050005b3480156100e857600080fd5b5061011b600480360360208110156100ff57600080fd5b81019080803563ffffffff169060200190929190505050610131565b6040518082815260200191505060405180910390f35b6000602052806000526040600020600091509050548156fea2646970667358221220f5b12b5cf2d3d7907e2d36e5751ea15fd120efe5955353a77fa6c880982622c864736f6c63430006060033"
raw_deploy = ch.transaction_obj(gas=180000, data=bytecode, value=0, to="")
deploy_hash = eth.sendRawTransaction(raw_deploy)
deploy_receipt = None
while not deploy_receipt:
    deploy_receipt = eth.getTransactionReceipt(deploy_hash)
    time.sleep(0.1)

print(str(deploy_receipt))

contractAddress = deploy_receipt["contractAddress"]
print(f"contractAddress={contractAddress}")
code = eth.getCode(contractAddress)
print(f"code={code}")

CHUNK_SIZE=1024*1024
nchunks = (storage_size + CHUNK_SIZE - 1) // CHUNK_SIZE

for i in range (nchunks):
  raw_call = ch.transaction_obj(gas=180000 + CHUNK_SIZE * 21000, to=contractAddress, value=storage_size)
  call_hash = eth.sendRawTransaction(raw_call)
  call_receipt = None
  while not call_receipt:
      call_receipt = eth.getTransactionReceipt(call_hash)
      time.sleep(0.1)
  print(str(call_receipt))
  print(f"i = {i} of {nchunks}")

print(f"Filled {nchunks * CHUNK_SIZE} elements")

print('Stopping')
ch.stop()
print("Stopped")
