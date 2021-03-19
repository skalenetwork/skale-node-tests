import sys
import time

import web3
from web3.auto import w3

def compare_nodes(*eth):
    if len(eth) == 1:
        eth = eth[0]

    bn1 = 0
    bn2 = 0

    ok = True

    try:
        bn1 = eth[0].blockNumber
    except:
        pass
    try:
        bn2 = eth[1].blockNumber
    except:
        pass
    
    bn = max(bn1, bn2)
    
    b = 0
    have_printed_hashes = False
    while b <= bn:
        line = ""
        arr_tx = []
        arr_hash = []
        for e in eth:
            try:
                block = e.getBlock(b)
                val = len(block.transactions)
                line += str(val) + " "
                arr_tx.append(val)
                arr_hash.append(block.hash)
            except Exception as ex:
                print(f"Endpoint {e.web3.provider.endpoint_uri} is unavailable")
                b = bn # exit
                ok = False
                break
                #b -= 1
                #time.sleep(1)
                #break

        equal_tx = True
        equal_hash = True
        if len(arr_tx)==len(eth):
            equal_tx = all(arr_tx[0]==e for e in arr_tx)
            equal_hash = all(arr_hash[0]==e for e in arr_hash)

        if (not equal_tx) or (not equal_hash and not have_printed_hashes):
            print(f"\nblock {b}: {line}", end='')
            if not equal_hash and not have_printed_hashes:
                print(" " + str(arr_hash))
                have_printed_hashes = True
            else:
                print()
            ok = False
        else:
            print('.', end='')

        b += 1
        
    return ok

def main():
    nodes = []

    for url in sys.argv[1:]:

        if url.lower().startswith("http"):
            provider = web3.Web3.HTTPProvider(url)
        elif url.lower().startswith("ws"):
            provider = web3.Web3.WebsocketProvider(url)
        else:
            provider = web3.Web3.IPCProvider(url)

        if not provider.isConnected():
            print(f"Cannot connect to {url}")
            exit(1)

        print(f"Connected to {url} via object w3")

        nodes.append(web3.Web3(provider).eth)
        
    print(compare_nodes(nodes))

if __name__ == "__main__":
    main()
