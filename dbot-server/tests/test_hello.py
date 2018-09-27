#!/usr/bin/python
# -*- coding: utf-8 -*-

from app import create_app
import unittest
import json


class APIV1TestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(environment="Testing")

    def test_hello_version(self):
        data = json.loads(self.app.test_client().get('/api/v0/hello').data)
        assert data.get('version') == 0
        assert data.get('data') == 'hello world!'
