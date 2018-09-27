#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import click
import logging
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from eth_account import Account
from requests.exceptions import HTTPError

from microraiden.config import NETWORK_CFG

from .service import DBotService
from .metric import DBotApiMetric
from app import db
from dbot_metrics import DBotMetricsCollector
from utils import load_module

logger = logging.getLogger('dbot.' + os.path.splitext(os.path.basename(__file__))[0])


class DBotServer:

    instance = None

    def __init__(self, *args, **kwargs):
        raise RuntimeError("Not allowed to instantiate this class directly,"
                           " use new() method instead")

    @classmethod
    def new(cls):
        if cls.instance is None:
            cls.instance = cls.__new__(cls)
            cls.instance.services = {}
            cls.web3 = None

        return cls.instance

    def init(self, app, private_key, http_provider=None):
        self.account = Account.privateKeyToAccount(private_key)
        self.web3 = Web3(HTTPProvider(
            app.config['WEB3_PROVIDER_DEFAULT'] if http_provider is None else http_provider))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)
        try:
            NETWORK_CFG.set_defaults(int(self.web3.version.network))
        except HTTPError as err:
            logger.error('Can not connect with blockchain node: {}'.format(err))
            raise HTTPError

        self.state_path = os.path.join(app.config['DB_ROOT'], 'channels')
        if not os.path.exists(self.state_path):
            os.makedirs(self.state_path)

        logger.info("load all exist dbot service")
        dbot_address_list = db.dbots.keys()
        for address in dbot_address_list:
            dbot_data = db.dbots.get(address)
            mw = dbot_data.get('middleware')
            if mw:
                mw_path = os.path.join(db.path(), 'middleware/{}'.format(address))
                middleware = getattr(load_module(mw['module'], mw_path), mw['class'])
                self.new_service(dbot_data, middleware)
            else:
                self.new_service(dbot_data)

        logger.info("start metric collector")
        DBotMetricsCollector().Start(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "collector.conf"))
        self.metric = DBotApiMetric()
        DBotMetricsCollector().RegisterMetric(self.metric)
        self.metric.EnableDetailRecord(False)

        self.rest_server = None
        self.server_greenlet = None

    def new_service(self, data, middleware=None):
        name = data['info']['name']
        domain = data['info']['domain']
        dbot_address = data['info']['addr']
        state_file = os.path.join(self.state_path, '{}.db'.format(dbot_address))
        logger.info('instantiate a dbot service: {}({})'.format(name, dbot_address))
        dbot_service = DBotService(self.account.privateKey.hex(), self.web3, state_file, data, middleware)
        dbot_service.start()
        self.services[dbot_address] = dbot_service

    def update_service(self, data, address, middleware=None):
        dbot_service = self.get_service(address)
        if dbot_service:
            dbot_service.update(data, middleware)

    def get_service(self, dbot_address):
        return self.services.get(dbot_address)

    def remove_service(self, dbot_address):
        dbot_service = self.get_service(dbot_address)
        if dbot_service:
            dbot_service.stop()

    def wait_sync(self):
        for k in self.services:
            self.services[k].wait_sync()

    def stop(self):
        DBotMetricsCollector().Stop()
        for k in self.services:
            self.services[k].stop()
