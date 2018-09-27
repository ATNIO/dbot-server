#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paste swagger specification file
"""
import os
import json

from utils import Cached

class SwaggerParser(metaclass=Cached):
    def __init__(self, filename, filehander=None):
        if filehander is None:
            with open(filename, 'r') as fh:
                self._spec = json.load(fh)
        else:
            self._spec = json.load(filehander)
        self._load_spec()

    def _load_spec(self):
        # TODO use schema to check if specification is valid.
        if self._spec.get('swagger') != '2.0':
            raise Exception('Dbot specification only support swagger 2.0 now.')
        try:
            self.api_host = self._spec['host']
            self.protocol = 'https' if 'https' in self._spec['schemes'] else 'http'
            self.endpoints = []
            basePath = self._spec.get('basePath', '')
            for path, path_value in self._spec['paths'].items():
                uri = basePath + path
                for method, method_value in path_value.items():
                    self.endpoints.append({
                        'uri': uri,
                        'method': method
                    })
        except Exception as err:
            raise Exception('Parse dbot specification failed: {}'.format(err))

    def dumps(self):
        return json.dumps(self._spec)
