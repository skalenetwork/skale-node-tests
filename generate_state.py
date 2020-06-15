from sktest import *
from sktest_helpers import *
import time
import sys

global storage_size
storage_size = int(sys.argv[1])

ch = create_default_chain(num_nodes=1, num_accounts=2)
ch.start()

eth = ch.nodes[0].eth

#pragma solidity >=0.4.10 <0.7.0;
#
#
#contract StorageFiller{
#    
#    mapping (uint32 => bytes32) public store;
#    
#    fallback() external payable {
#        uint n = msg.value;
#        for(uint32 i=0; i<n; ++i){
#            store[i] = keccak256(abi.encodePacked(block.number)) ^ keccak256(abi.encodePacked(i));
#        }// for
#        
#    }// fallback
#}

bytecode = "608060405234801561001057600080fd5b5061016e806100206000396000f3fe6080604052600436106100225760003560e01c8063b9e95382146100cb57610023565b5b600034905060008090505b818163ffffffff1610156100c75780604051602001808263ffffffff1663ffffffff1660e01b815260040191505060405160208183030381529060405280519060200120436040516020018082815260200191505060405160208183030381529060405280519060200120186000808363ffffffff1663ffffffff1681526020019081526020016000208190555080600101905061002e565b5050005b3480156100d757600080fd5b5061010a600480360360208110156100ee57600080fd5b81019080803563ffffffff169060200190929190505050610120565b6040518082815260200191505060405180910390f35b6000602052806000526040600020600091509050548156fea26469706673582212201e9b561a8054c4131f95f71ed26d64a95b3a37f9489136a0bb3bde5315fa9cc364736f6c63430006060033"

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
  raw_call = ch.transaction_obj(gas=181000 + CHUNK_SIZE * 99000, to=contractAddress, value=CHUNK_SIZE)
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
