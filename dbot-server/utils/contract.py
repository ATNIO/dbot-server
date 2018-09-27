#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List, Any, Union, Dict
from web3.contract import Contract

def create_signed_contract_transaction(
        private_key: str,
        contract: Contract,
        func_name: str,
        args: List[Any]
):
    w3 = contract.web3
    acct = w3.eth.account.privateKeyToAccount(private_key)
    if name == 'constructor':
        tx_data = contract.constructor(*args).buildTransaction({
            'from': acct.address,
            'nonce': web3.eth.getTransactionCount(acct.address),
            'gasPrice': web3.eth.gasPrice
        })
    else:
        tx_data = contract.functions[func_name](*args).buildTransaction({
            'from': acct.address,
            'nonce': web3.eth.getTransactionCount(acct.address),
            'gasPrice': web3.eth.gasPrice
        })
    signed_tx = acct.signTransaction(tx_data)
    return signed_tx.rawTransaction
