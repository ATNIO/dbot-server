#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import logging
import re
from werkzeug.routing import Map, Rule, NotFound, MethodNotAllowed
from werkzeug import Request, Response, MultiDict
from eth_utils import is_address, to_checksum_address
from werkzeug.datastructures import EnvironHeaders

from utils import remove_slash_prefix
from .errors import InvalidUsage
import dbot

logger = logging.getLogger('dbot.' + os.path.splitext(os.path.basename(__file__))[0])


def _match_uri(template, uri):
    # TODO match uri with the define in swagger spec file
    template = remove_slash_prefix(template)
    uri = remove_slash_prefix(uri)
    pattern = ''
    in_bracket = False
    for c in template:
        if in_bracket:
            continue
        if c == '{':
            in_bracket = True
            continue
        if c == '}':
            in_bracket = False
            pattern = pattern + '.+'
            continue
        pattern = pattern + c
    return True if re.match(pattern, uri) else False

def _match_method(method1, method2):
    return method1.upper() == method2.upper()


def _get_endpoint(dbot_service, uri, method):
    for endpoint in dbot_service.endpoints:
        if _match_uri(endpoint['uri'], uri) and _match_method(endpoint['method'], method):
            proxy_uri = endpoint['path']
            price = endpoint['price']
            return price, proxy_uri
    return -1, None

def _make_response(environ, start_response, data, code, headers={}):
    headers['Access-Control-Allow-Origin'] = environ.get('HTTP_ORIGIN', '*')
    response = Response(response=data, status=code, headers=headers)
    return response(environ, start_response)

class DbotMiddleware():
    def __init__(self, wsgi_app):
        self.app = wsgi_app

    def __call__(self, environ, start_response):
        # this middleware only used for (/call/<dbot_address>/<path:uri>
        url_map = Map([
            Rule('/call/<dbot_address>/<path:uri>', endpoint='proxy')
        ])
        urls = url_map.bind_to_environ(environ)
        try:
            endpoint, kwargs = urls.match()
        except (NotFound, MethodNotAllowed) as e:
            return self.app(environ, start_response)

        try:
            method = environ['REQUEST_METHOD']
            if method == 'OPTIONS':
                # if CORS first request, return response
                return self.app(environ, start_response)

            dbot_address = kwargs['dbot_address']
            dbot_address = to_checksum_address(dbot_address)
            uri = kwargs['uri']
            dbot_service = dbot.get_service(dbot_address)
            if not dbot_service:
                raise InvalidUsage('dbot address not found', status_code=404)

            # Ensure the URI is an approved API endpoint, else abort
            price, proxy_uri = _get_endpoint(dbot_service, uri, method)
            if price < 0:
                logger.error("({}: {}) is not an approved API endpoint.".format(method, uri))
                raise InvalidUsage("({}: {}) is not an approved API endpoint.".format(method, uri), status_code=404)

            environ['PATH_INFO'] = '/call/{}/{}'.format(dbot_address, remove_slash_prefix(proxy_uri))
            if price > 0:
                # Balance Proof check
                ret, code, headers = dbot_service.paywall.access(price, EnvironHeaders(environ))
                if code != 200:
                    return _make_response(environ, start_response, ret, code, headers)

            logger.info("Balance Proof check is ok.")
            middleware_cls = dbot_service.middleware
            if middleware_cls:
                # load dbot's middleware in runtime
                logger.info('init middleware({}) for dbot({})'.format(middleware_cls, dbot_address))
                middleware = middleware_cls(self.app)
                return middleware(environ, start_response)
            else:
                return self.app(environ, start_response)
        except InvalidUsage as e:
            logger.error('{}'.format(e.message))
            return _make_response(environ, start_response,
                                  '{}'.format(e.to_dict()), e.status_code)
        except Exception as e:
            logger.error('{}'.format(e))
            return _make_response(environ, start_response, '{}'.format(e), 500)
