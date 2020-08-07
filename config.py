import json
import copy
import os
import sys
import collections
from hexbytes import HexBytes

# (c) https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
def _dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            _dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]

class _HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)

def merge(base, more):
    _dict_merge(base, more)

def to_string(config):
    return json.dumps(config, indent = 1, cls = _HexJsonEncoder)

def _merge_cmd( arr_files ):
    res = {}
    for name in arr_files:
        with open(name, "r") as f:
            obj = json.load( f )
            _dict_merge( res, obj )
            
    return to_string( res )

def _usage():
    print("USAGE:")
    print("python3 " + sys.argv[0] + " merge file1.json [file2.json...]")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        _usage()
        exit()
    if( sys.argv[1] == "merge"):
        res = _merge(sys.argv[2:])
        print( res )
    else:
        _usage()
        exit()
