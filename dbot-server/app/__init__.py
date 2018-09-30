#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from flask import Flask, jsonify
import logging

from .database import Database
from .errors import InvalidUsage

db = Database()

def create_app(name=None, environment=None):
    app = Flask(__name__ if name is None else name)

    from flask_cors import CORS
    cors = CORS(app, resources={r"*": {"origins": "*"}})

    app.config['CORS_HEADERS'] = 'Content-Type'

    if not environment:
        environment = os.environ.get('FLASK_CONFIG', 'development')
    app.config.from_object('config.{}'.format(environment.capitalize()))
    app.config.from_pyfile(
        'config_{}.py'.format(environment.lower()),
        silent=True
    )

    @app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.route('/')
    def root():
        return "DBot Server is running", 200

    db.init_app(app)

    from .api import dbots_v1, api_root
    app.add_url_rule('{}/v1'.format(app.config['URL_PREFIX']), 'api_root', api_root)

    app.register_blueprint(
        dbots_v1.bp,
        url_prefix='{}/v{}'.format(app.config['URL_PREFIX'], dbots_v1.bp.api_version)
    )

    from .proxy import bp as proxy_bp
    app.register_blueprint(proxy_bp)

    from .metric import bp as metric_bp
    app.register_blueprint(metric_bp)

    from .middleware import DbotMiddleware
    app.wsgi_app = DbotMiddleware(app.wsgi_app)

    return app
