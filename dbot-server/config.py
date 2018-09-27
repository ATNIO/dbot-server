#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json


# config class for flask

class Config(object):
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = 4548
    URL_PREFIX = '/api'
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    TEMPLATE_FOLDER = os.path.join(PROJECT_ROOT, 'templates')
    DB_ROOT = os.path.join(PROJECT_ROOT, 'data')
    WEB3_PROVIDER_DEFAULT = "http://0.0.0.0:4545"


class Development(Config):
    DEBUG = True
    SECRET_KEY = 'development'


class Production(Config):
    HOST = '0.0.0.0'
    PORT = 80

class Testing(Config):
    TESTING = True
    SECRET_KEY = 'testing'


# config for dbot

