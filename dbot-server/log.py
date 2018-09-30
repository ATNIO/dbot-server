#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from logging.handlers import RotatingFileHandler

import config

LOGPATH = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGPATH, exist_ok=True)

class DBotLogger():
    def __init__(self, name, app_environ):
        self._name=name
        self._app_config = getattr(config, app_environ)
        print('self._dbug = {}'.format(self._app_config.DEBUG))

    def config(self):
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '%(asctime)s %(name)s(%(levelname)s) %(message)s (%(filename)s[%(lineno)d])'
                },
                'normal': {
                    'format': '%(asctime)s %(levelname)-8s %(message)s'
                },
                'simple': {
                    'format': '%(levelname)s %(message)s'
                },
            },
            'handlers': {
                'console':{
                    'level': 'INFO',
                    'class':'logging.StreamHandler',
                    'formatter': 'simple'
                },
                'info_file': {
                    'level': 'INFO',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'formatter': 'normal',
                    'filename': os.path.join(LOGPATH, '{}.log'.format(self._name)),
                    'encoding': 'utf8',
                    'mode': 'a',
                    'maxBytes': 10485760,
                    'backupCount': 5
                },
                'debug_file': {
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'formatter': 'verbose',
                    'filename': os.path.join(LOGPATH, '{}_debug.log'.format(self._name)),
                    'encoding': 'utf8',
                    'mode': 'a',
                    'maxBytes': 10485760,
                    'backupCount': 20
                },
            },
            'loggers': {
                'dbot': {
                    'handlers': ['console', 'info_file', 'debug_file'],
                    'level': 'DEBUG' if self._app_config.DEBUG else 'INFO',
                    'propagate': False
                }
            },
            'root': {
                'handlers': ['console', 'info_file', 'debug_file'],
                'level': 'DEBUG' if self._app_config.DEBUG else 'INFO',
            }
        }
