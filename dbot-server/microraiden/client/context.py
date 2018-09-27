import os
import json
from web3 import Web3

from microraiden.constants import CONTRACT_METADATA, CHANNEL_MANAGER_NAME
from microraiden.utils import privkey_to_addr


def _make_dbot_contract(web3, dbot_address):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../contracts/contracts.json')) as fh:
        contracts = json.load(fh)
    dbot_address = Web3.toChecksumAddress(dbot_address)
    dbotContract = web3.eth.contract(address=dbot_address,
                                     abi=contracts['Dbot']['abi'],
                                     bytecode=contracts['Dbot']['bytecode'])
    return dbotContract


class Context(object):
    def __init__(
            self,
            private_key: str,
            web3: Web3,
            channel_manager_address: str
    ):
        self.private_key = private_key
        self.address = privkey_to_addr(private_key)
        self.web3 = web3

        self.channel_manager = web3.eth.contract(
            address=channel_manager_address,
            abi=CONTRACT_METADATA[CHANNEL_MANAGER_NAME]['abi']
        )

        #  token_address = self.channel_manager.call().token()
        #  self.token = web3.eth.contract(
        #      address=token_address,
        #      abi=CONTRACT_METADATA[TOKEN_ABI_NAME]['abi']
        #  )

    def make_dbot_contract(self, dbot_address):
        return _make_dbot_contract(self.web3, dbot_address)
