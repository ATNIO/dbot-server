#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()
import click

import os
import json
import signal
import gevent
import logging
import logging.config

from app import create_app
from utils import get_private_key

os.makedirs('logs', exist_ok=True)
logging.config.fileConfig(os.path.join(os.path.dirname(__file__), 'logging.conf'))

app = create_app()
if app.config['DEBUG']:
    logging.getLogger('dbot').setLevel(logging.DEBUG)
else:
    logging.getLogger('dbot').setLevel(logging.INFO)

def handle_quit(sig, frame):
    logging.info("handle_quit called with signal {}".format(sig))
    logging.info("Stop Dbot Server ...")
    import dbot
    dbot_server = dbot.get_server()
    dbot_server.stop()
    exit(0)


@click.group()
def cli():
    pass

@cli.command()
@click.option(
    '--host',
    default=app.config['HOST'],
    help='server host'
)
@click.option(
    '--port',
    default=app.config['PORT'],
    help='server port'
)
@click.option(
    '--pk-file',
    help='private_key file'
)
@click.option(
    '--pw-file',
    default = None,
    help='password file for private_key'
)
@click.option(
    '--http-provider',
    default = None,
    help='private_key file'
)
def run_server(host, port, pk_file, pw_file, http_provider):
    private_key = get_private_key(pk_file, pw_file)
    import dbot
    dbot_server = dbot.get_server()
    dbot_server.init(app, private_key, http_provider)
    # save dbot backend info for dbot-service tool to operate dbot-service
    app_dir = os.path.join(os.path.expanduser('~'), '.dbot-server')
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    with open(os.path.join(app_dir, '.backend'), 'w') as fh:
        json.dump({
            'backend': 'http://{}:{}'.format(host, port),
            'pk_file': os.path.abspath(pk_file),
            'pw_file': os.path.abspath(pw_file),
            'http_provider': http_provider
        }, fh, indent=2)
    app.run(host=host, port=port, debug=app.config['DEBUG'], use_reloader=False)


if __name__ == '__main__':
    signal.signal(signal.SIGHUP, handle_quit)
    signal.signal(signal.SIGTERM, handle_quit)
    signal.signal(signal.SIGINT, handle_quit)
    cli()
