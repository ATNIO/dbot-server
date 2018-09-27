#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
'''

import os
import logging
from flask import Blueprint, request, Response, make_response
import requests


import dbot
from utils import remove_slash_prefix
from .decorates import api_metric, middleware, checksum_address
from .errors import InvalidUsage

logger = logging.getLogger('dbot.' + os.path.splitext(os.path.basename(__file__))[0])

bp = Blueprint('proxy', __name__)


@bp.route('/call/<dbot_address>/<path:uri>', methods=["GET", "POST"])
@api_metric
@checksum_address
def proxy(dbot_address, uri, proxy_uri=None):
    # proxy requst to api server host
    dbot_service = dbot.get_service(dbot_address)
    if not dbot_service:
        raise InvalidUsage('dbot address not found', status_code=404)
    url = '{}://{}/{}'.format(dbot_service.protocol, dbot_service.api_host, remove_slash_prefix(uri))
    headers = {key: value for (key, value) in request.headers if key != 'Host'}
    # Pass original Referer for subsequent resource requests
    headers["Referer"] = url

    logger.info("Proxy the API {}: {}, with headers: \n{}".format(request.method, url, headers))

    # Fetch the URL, and stream it back
    try:
        resp = requests.request(
            url=url,
            method=request.method,
            params=request.args,
            headers=headers,
            #  TODO: Usually it's a bad idea to call get_data() without checking the
            #  content length first as a client could send dozens of megabytes or more
            #  to cause memory problems on the server.
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False)

        logger.info("Got {} response from {}".format(resp.status_code, url))

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                if name.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, headers)
    except Exception as err:
        raise InvalidUsage('Cannot proxy the request.\n{}'.format(err), status_code=400)
