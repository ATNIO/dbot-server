#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
import cloudpickle
from flask import Blueprint, request
from flask_restful import Api, Resource, fields, marshal_with, abort, reqparse
from eth_utils import is_same_address, to_checksum_address
import logging
from werkzeug.utils import secure_filename


from app import db
from app.decorates import requires_signature, checksum_address
from utils import load_module
import dbot

logger = logging.getLogger('dbot.' + os.path.splitext(os.path.basename(__file__))[0])

API_VERSION = 1

bp = Blueprint('dbots_v1', __name__)
bp.api_version = API_VERSION
api = Api(bp)

info_fields = {
    "name": fields.String,
    "domain": fields.String,
    "description": fields.String,
    "logo": fields.String,
    "category": fields.String,
    "tags": fields.List(fields.String),
    "addr": fields.String,
    "owner": fields.String,
    "floor_price": fields.String
}

endpoint_fields = {
    'uri': fields.String,
    'path': fields.String,
    'method': fields.String,
    'price': fields.String
}

specification_fields = {
    'type': fields.String,
    'format': fields.String,
    'data': fields.String
}

dbot_fields = {
    "info": fields.Nested(info_fields),
    "endpoints": fields.List(fields.Nested(endpoint_fields)),
    "specification": fields.Nested(specification_fields)
}

dbot_list_fields = {
    "info": fields.Nested(info_fields),
    "endpoints": fields.List(fields.Nested(endpoint_fields))
}

class TopupTXs(fields.Raw):
    def format(self, value):
        return {k if isinstance(k, str) else '0x' + k.hex(): str(v) for k, v in value.items()}

class ChannelState(fields.String):
    def format(self, value):
        return str(value).split(r'.')[1]

channel_fields = {
    "receiver": fields.String,
    "sender": fields.String,
    "open_block_number": fields.String,
    "deposit": fields.String,
    "balance": fields.String,
    #  "last_signature": fields.String,
    "state": ChannelState,
    "settle_block_number": fields.String(attribute='settle_timeout'),
    #  "create_at": fields.Integer(attribute='ctime'),
    #  "update_at": fields.Integer(attribute='mtime'),
    "confirmed": fields.Boolean,
    "unconfirmed_topups": TopupTXs
}


class DBotList(Resource):

    def __init__(self):
        super(DBotList, self).__init__()

    @marshal_with(dbot_list_fields)
    def get(self):
        return  db.dbots.all()

    def post(self):
        """
        New a Dbot
        This API need authorization with signature in headers
        """
        # TODO request data valid check
        profile = request.files['profile']
        specification = request.files['specification']
        form = request.form
        dbot_data = json.load(profile)

        domain = form.get('domain', dbot_data['info'].get('domain'))
        if domain is None:
            abort(400, message="DBot domain is required")
        dbot_data['info'].update({
            'addr': form['address'],
            'owner': form['owner'],
            'floor_price': form['floor_price'],
            'api_host': form['api_host'],
            'protocol': form['protocol'],
            'domain': domain
        })
        dbot_data['specification']['data'] = specification.read().decode('utf-8')
        address = to_checksum_address(dbot_data['info'].get('addr'))
        if db.dbots.get(address) is not None:
            abort(404, message="Bad Request, can not insert an exsit DBot service")
        dbot_data['info']['addr'] = address
        middleware = None
        try:
            mw = dbot_data.get('middleware')
            if mw:
                mw_path = os.path.join(db.path(), 'middleware/{}'.format(address))
                if not os.path.exists(mw_path):
                    os.makedirs(mw_path)
                request.files.get('middleware').save(os.path.join(mw_path, '{}.py'.format(mw['module'])))
                middleware = getattr(load_module(mw['module'], mw_path), mw['class'])
        except Exception as err:
            abort(400, message='unable to load DBot middleware: {}'.format(err))
        try:
            dbot.new_service(dbot_data, middleware)
        except Exception as err:
            abort(400, message=str(err))
        db.dbots.put(address, dbot_data)

        return 'ok', 200

class DBotDetail(Resource):

    @marshal_with(dbot_fields)
    @checksum_address
    def get(self, dbot_address):
        data = db.dbots.get(dbot_address)
        if data is None:
            abort(404, message="DBot not found")
        else:
            assert(dbot_address == data['info']['addr'])
            return data

    @checksum_address
    def delete(self, dbot_address):
        if db.dbots.get(dbot_address) is None:
            abort(404, message="DBot not found")
        try:
            dbot.remove_service(dbot_address)
        except Exception as err:
            abort(400, message=err)
        db.dbots.delete(dbot_address)
        return 'ok', 200

    @checksum_address
    def put(self, dbot_address):
        profile = request.files['profile']
        specification = request.files['specification']
        form = request.form
        dbot_data = json.load(profile)
        domain = form.get('domain', dbot_data['info'].get('domain'))
        if domain is None:
            abort(400, message="DBot domain is required")
        dbot_data['info'].update({
            'addr': form['address'],
            'owner': form['owner'],
            'floor_price': form['floor_price'],
            'api_host': form['api_host'],
            'protocol': form['protocol'],
            'domain': domain
        })
        dbot_data['specification']['data'] = specification.read().decode('utf-8')
        if not is_same_address(dbot_data['info']['addr'], dbot_address):
            abort(400, message="Bad Request, wrong address in DBot data")

        dbot_address = to_checksum_address(dbot_address)
        dbot_data['info']['addr'] = dbot_address

        middleware = None
        try:
            # TODO update middleware (delete old one)
            mw = dbot_data.get('middleware')
            if mw:
                mw_path = os.path.join(db.path(), 'middleware/{}'.format(dbot_address))
                if not os.path.exists(mw_path):
                    os.makedirs(mw_path)
                request.files.get('middleware').save(os.path.join(mw_path, '{}.py'.format(mw['module'])))
                middleware = getattr(load_module(mw['module'], mw_path), mw['class'])
        except Exception as err:
            abort(400, message='unable to load DBot middleware: {}'.format(err))

        try:
            dbot.update_service(dbot_data, dbot_address, middleware)
        except Exception as err:
            abort(400, message=str(err))
        db.dbots.put(dbot_address, dbot_data)
        return 'ok', 200


class DBotChannelList(Resource):
    @staticmethod
    def get(dbot_address, sender_address=None):
        return ChannelList.get(dbot_address, sender_address)


class DBotChannelDetail(Resource):
    @staticmethod
    def get(dbot_address, sender_address, block_number):
        return ChannelDetail.get(dbot_address, sender_address, block_number)

    @staticmethod
    def delete(dbot_address, sender_address, block_number):
        return ChannelDetail.delete(dbot_address, sender_address, block_number)


class ChannelList(Resource):
    @staticmethod
    @marshal_with(channel_fields)
    @checksum_address
    def get(receiver_address, sender_address=None):
        dbot_address = receiver_address
        dbot_service = dbot.get_service(dbot_address)
        if not dbot_service:
            abort(404, message="dbot not found")
        return dbot_service.channel_list.get(sender_address)

    #  @staticmethod
    #  @checksum_address
    #  def delete(receiver_address, sender_address):
    #      dbot_address = receiver_address
    #      dbot_service = dbot.get_service(dbot_address)
    #      if not dbot_service:
    #          abort(404, message="dbot not found")
    #      return dbot_service.channel_list.delete(sender_address)


class ChannelDetail(Resource):
    @staticmethod
    @marshal_with(channel_fields)
    @checksum_address
    def get(receiver_address, sender_address, block_number):
        dbot_address = receiver_address
        dbot_service = dbot.get_service(dbot_address)
        if not dbot_service:
            abort(404, message="dbot not found")
        ret, status_code = dbot_service.channel_detail.get(sender_address, block_number)
        if status_code != 200:
            abort(status_code, message=ret)
        return ret, status_code

    @staticmethod
    @checksum_address
    def delete(receiver_address, sender_address, block_number):
        dbot_address = receiver_address
        dbot_service = dbot.get_service(dbot_address)
        if not dbot_service:
            abort(404, message="dbot not found")
        return dbot_service.channel_detail.delete(sender_address, block_number)


api.add_resource(DBotList, '/dbots')
#  api.add_resource(DBot1List, '/dbots1')
api.add_resource(DBotDetail, '/dbots/<string:dbot_address>')
api.add_resource(DBotChannelList, '/dbots/<string:dbot_address>/channels',
                 '/dbots/<string:dbot_address>/channels/<string:sender_address>')
api.add_resource(DBotChannelDetail, '/dbots/<string:dbot_address>/channels/<sender_address>/<int:block_number>')
api.add_resource(ChannelList, '/channels/<string:receiver_address>',
                 '/channels/<string:receiver_address>/<string:sender_address>')
api.add_resource(ChannelDetail, '/channels/<string:receiver_address>/<sender_address>/<int:block_number>')
