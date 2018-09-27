#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
from functools import wraps
from flask import request
from eth_account.messages import defunct_hash_message
import logging
from eth_utils import is_address, is_same_address, to_checksum_address

import dbot

logger = logging.getLogger('dbot.' + os.path.splitext(os.path.basename(__file__))[0])


def requires_signature(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        w3 = dbot.get_server().web3
        signature = request.headers.get('signature')
        if signature is None:
            return "DBot owner's signature is required to start an DBot service", 401
        payload = request.data
        msg_hash = defunct_hash_message(payload)
        sig_address = w3.eth.account.recoverHash(msg_hash, signature=signature)
        server_owner = dbot.get_server().account.address
        if not is_same_address(sig_address, server_owner):
            return "Only the server's owner({}) can change dbot services on it".format(server_owner), 401

        dbot_address = kwargs.get('dbot_address')
        if request.method != 'DELETE':
            len = request.headers.get('len')
            if len:
                data_len = int(len)
            else:
                return "Bad Request, data length is require in headers", 404
            dbot_data = json.loads(payload[:data_len].decode('utf-8'))
            if dbot_address is None:
                dbot_address = dbot_data['info']['addr']

        dbot_contract = dbot.make_contract(w3, dbot_address)
        dbot_owner = dbot_contract.functions.getOwner().call()
        logger.debug("Signer's address is {}, Dbot(address = {}) owner is {}.".format(
            sig_address, dbot_address, dbot_owner))
        if not is_same_address(sig_address, dbot_owner):
            return "Signature mismatch with DBot owner, signer is {}, dbot owner is {}".format(
                sig_address, dbot_owner
            ), 401
        return f(*args, **kwargs)
    return decorated


def api_metric(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        metric = dbot.get_server().metric
        endpoint = request.url
        caller = request.remote_addr
        apiinfo = metric.CallBegin(endpoint, caller)
        response = f(*args, **kwargs)
        metric.CallEnd(apiinfo, response.status_code)
        return response
    return decorated


def checksum_address(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        new_args = [to_checksum_address(arg) if is_address(arg) else arg for arg in args]
        new_kwargs = {k: to_checksum_address(v) if is_address(v) else v for k, v in kwargs.items()}
        return f(*new_args, **new_kwargs)
    return decorated


def middleware(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        dbot_address = kwargs.get('dbot_address')
        middleware = dbot.get_service(dbot_address).middleware
        request.new_method, request.new_args, request.new_headers, request.new_data = middleware(
            request.method, request.args, request.headers, request.get_data())
        return f(*args, **kwargs)
    return decorated
