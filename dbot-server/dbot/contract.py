#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from eth_utils import to_checksum_address


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../contracts/contracts.json')) as fh:
    CONTRACTS_METADATA = json.load(fh)

def get_abi_bytecode(channel_manager_address):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                '../../contracts/dbot/contract/DbotFactory.sol'), 'r') as fh:
        source = fh.read().replace('0x0000000000000000000000000000000000000012',
                                   to_checksum_address(channel_manager_address))
        from solc import compile_source
        _compiled_sol = compile_source(source)
        abi = _compiled_sol['<stdin>:Dbot']['abi']
        bytecode = _compiled_sol['<stdin>:Dbot']['bin']
        return abi, bytecode
