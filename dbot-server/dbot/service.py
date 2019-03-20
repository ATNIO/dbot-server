#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gevent
import logging
import json
import pickle
from flask import Flask
from flask import request
from flask_restful.utils import unpack
from eth_utils import encode_hex, is_address, is_same_address, to_checksum_address
from web3 import Web3, HTTPProvider

from microraiden.config import NETWORK_CFG
from microraiden import HTTPHeaders
from microraiden.make_helpers import make_channel_manager
from microraiden.channel_manager import (
    ChannelManager,
)
from microraiden.exceptions import (
    NoOpenChannel,
    InvalidBalanceProof,
    InvalidBalanceAmount,
    InsufficientConfirmations
)
import microraiden.constants as constants
from microraiden.proxy.resources.request_data import RequestData
from microraiden.proxy.resources import (
    ChannelManagementListChannels,
    ChannelManagementChannelInfo
)


logger = logging.getLogger('dbot.' + os.path.splitext(os.path.basename(__file__))[0])


class DBotService():

    def __init__(self,
                 private_key: str,
                 web3: Web3,
                 state_file_path: str,
                 dbot_data: dict,
                 middleware: None = None
                 ) -> None:

        self.name = dbot_data['info']['name']
        self.domain = dbot_data['info']['domain']
        self.address = Web3.toChecksumAddress(dbot_data['info']['addr'])
        self.endpoints = dbot_data['endpoints']
        self.api_host = dbot_data['info']['api_host']
        self.protocol = dbot_data['info']['protocol']
        # TODO middleware should be attribute which can be update runtime
        self.middleware = middleware
        self.enable = True

        self.channel_manager = make_channel_manager(
            self.address,
            private_key,
            NETWORK_CFG.channel_manager_address,
            state_file_path,
            web3
        )
        self.paywall = Paywall(self.channel_manager)
        self.channel_list = ChannelManagementListChannels(self.channel_manager)
        self.channel_detail = ChannelManagementChannelInfo(self.channel_manager)

    def start(self):
        if self.enable:
            logger.info('start dbot service, address = {}'.format(self.address))
            self.channel_manager.start()
            # TODO can not block here, how to make sure sync is ready before dbot provide service.
            #  self.channel_manager.wait_sync()

    def stop(self):
        logger.info('stop dbot service, address = {}'.format(self.address))
        self.enable = False

    def update(self, dbot_data, middleware):
        logger.info('update dbot service, address = {}'.format(self.address))
        assert(is_same_address(self.address, dbot_data['info']['addr']))
        self.name = dbot_data['info']['name']
        self.domain = dbot_data['info']['domain']
        self.endpoints = dbot_data['endpoints']
        self.api_host = dbot_data['info']['api_host']
        self.protocol = dbot_data['info']['protocol']
        self.middleware = middleware


class Paywall(object):
    def __init__(self,
                 channel_manager: ChannelManager
                 ) -> None:
        super().__init__()
        assert is_address(channel_manager.channel_manager_contract.address)
        assert is_address(channel_manager.receiver)
        self.contract_address = channel_manager.channel_manager_contract.address
        self.receiver_address = channel_manager.receiver
        self.channel_manager = channel_manager
        self.count = 0

    def access(self, price, req_headers):
        if self.channel_manager.node_online() is False:
            return "Blockchain node is not responding", 502, {}
        try:
            data = RequestData(req_headers)
        except ValueError as e:
            return str(e), 409, {}

        logger.info('check balance signature in request header')
        logger.info('request data = {}'.format(req_headers))
        refused, ret, resp_headers = self.paywall_check(price, data)

        if refused:
            return ret, 402, resp_headers
        else:
            return ret, 200, resp_headers

    def paywall_check(self, price, data):
        """Check if the resource can be sent to the client.
        """
        headers = self.generate_headers(price)
        if not data.balance_signature:
            logger.warning('No balance signature in headers')
            return True, 'No balance signature', headers

        # try to get an existing channel
        try:
            channel = self.channel_manager.verify_balance_proof(
                data.sender_address, data.open_block_number,
                data.balance, data.balance_signature)
        except InsufficientConfirmations as e:
            logger.info('Refused payment: Insufficient confirmations (sender={})'.format(data.sender_address))
            headers.update({HTTPHeaders.INSUF_CONFS: "1"})
            return True, 'Insufficient confirmations', headers
        except NoOpenChannel as e:
            logger.error('Refused payment: Channel does not exist (sender={})'.format(data.sender_address))
            logger.error(NoOpenChannel)
            headers.update({HTTPHeaders.NONEXISTING_CHANNEL: "1"})
            return True, 'Channel does not exist', headers
        except InvalidBalanceAmount as e:
            logger.error('Refused payment: Invalid balance amount: {} (sender={})'.format(str(e), data.sender_address))
            headers.update({HTTPHeaders.INVALID_PROOF: 1})
            return True, 'Invalid balance amount', headers
        except InvalidBalanceProof as e:
            logger.error('Refused payment: Invalid balance proof: {} (sender={})'.format(str(e), data.sender_address))
            headers.update({HTTPHeaders.INVALID_PROOF: 1})
            return True, 'Invalid balance proof', headers

        # set headers to reflect channel state
        assert channel.sender is not None
        assert channel.balance >= 0
        headers.update(
            {
                HTTPHeaders.SENDER_ADDRESS: channel.sender,
                HTTPHeaders.SENDER_BALANCE: channel.balance
            })
        if channel.last_signature is not None:
            headers.update({HTTPHeaders.BALANCE_SIGNATURE: channel.last_signature})

        amount_sent = data.balance - channel.balance

        if amount_sent != 0 and amount_sent != price:
            headers[HTTPHeaders.INVALID_AMOUNT] = 1
            #  if difference is 0, it will be handled by channel manager
            logger.info('Invalid ammount')
            return True, 'Invalid ammount', headers

        # set the headers to reflect actual state of a channel
        try:
            self.channel_manager.register_payment(
                channel.sender,
                data.open_block_number,
                data.balance,
                data.balance_signature)
        except (InvalidBalanceAmount, InvalidBalanceProof):
            # balance sent to the proxy is less than in the previous proof
            logger.info('Invalid Balance Amount')
            return True, 'Invalid Balance Amount', headers

        # all ok, return premium content
        return False, 'ok', headers

    # when are these generated?
    def generate_headers(self, price: int):
        assert price > 0
        """Generate basic headers that are sent back for every request"""
        headers = {
            HTTPHeaders.GATEWAY_PATH: constants.API_PATH,
            HTTPHeaders.RECEIVER_ADDRESS: self.receiver_address,
            HTTPHeaders.CONTRACT_ADDRESS: self.contract_address,
            HTTPHeaders.PRICE: price,
            'Content-Type': 'application/json'
        }
        return headers
