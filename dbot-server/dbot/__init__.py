#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from web3 import Web3
import json

from .contract import CONTRACTS_METADATA, get_abi_bytecode
from .server import DBotServer
from .service import DBotService
from .metric import DBotApiMetric


dbot_server = DBotServer.new()


def make_contract(web3, dbot_address=None):
    if dbot_address:
        dbot_address = Web3.toChecksumAddress(dbot_address)
        dbotContract = web3.eth.contract(address=dbot_address,
                                         abi=CONTRACTS_METADATA['Dbot']['abi'],
                                         bytecode=CONTRACTS_METADATA['Dbot']['bytecode'])
    else:
        dbotContract = web3.eth.contract(abi=CONTRACTS_METADATA['Dbot']['abi'],
                                         bytecode=CONTRACTS_METADATA['Dbot']['bytecode'])
    return dbotContract

def get_server():
    return dbot_server


def get_service(dbot_address):
    return dbot_server.get_service(dbot_address)


def new_service(dbot_data, middleware):
    return dbot_server.new_service(dbot_data, middleware)


def update_service(dbot_data, dbot_address, middleware):
    return dbot_server.update_service(dbot_data, dbot_address, middleware)


def remove_service(dbot_address):
    return dbot_server.remove_service(dbot_address)


__all__ = [
    DBotApiMetric,
    make_contract,
    get_server,
    get_service,
    new_service,
    update_service,
    remove_service,
    CONTRACTS_METADATA,
    get_abi_bytecode
]
