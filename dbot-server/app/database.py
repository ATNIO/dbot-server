#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Module for DB.

'''
import os
import abc
import leveldb
import logging
import json
from collections import MutableMapping

from utils import Cached
from exceptions import DBException


logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class LevelDBDict(MutableMapping):
    def __init__(self, db_file):
        self.__db_file = db_file
        self.__db = leveldb.LevelDB(self.__db_file)

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, key):
        if type(key) not in [str, bytes]:
            raise DBException('Key should be str or bytes')
        k = key if isinstance(key, bytes) else key.encode('utf-8')
        return self.__db.Get(k)

    def __setitem__(self, key, value):
        if type(key) not in [str, bytes]:
            raise DBException('Key should be str or bytes')
        k = key if isinstance(key, bytes) else key.encode('utf-8')
        self.__db.Put(k, value)

    def __delitem__(self, key):
        if type(key) not in [str, bytes]:
            raise DBException('Key should be str or bytes')
        k = key if isinstance(key, bytes) else key.encode('utf-8')
        self.__db.Delete(k)

    def __iter__(self):
        for k in self.__db.RangeIter(include_value=False):
            try:
                yield k.decode('utf-8')
            except Exception:
                yield k

    def keys(self):
        return self.__iter__()

    def items(self):
        for k, v in self.__db.RangeIter():
            try:
                yield k.decode('utf-8'), v
            except Exception:
                yield k, v


    def writebatch(self, values):
        batch = leveldb.WriteBatch()
        for k, v in values.items():
            batch.Put(k, v)
        self.__db.Write(batch)


class LevelDBJsonDict(MutableMapping):
    def __init__(self, db_file):
        self.__db_file = db_file
        self.__db = leveldb.LevelDB(self.__db_file)

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise DBException('Key should be str')
        k = key.encode('utf-8')
        return json.loads(self.__db.Get(k).decode('utf-8'))

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise DBException('Key should be str')
        if not isinstance(value, dict):
            raise DBException('Value should be dict')
        k = key.encode('utf-8')
        v = json.dumps(value).encode('utf-8')
        self.__db.Put(k, v)

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise DBException('Key should be str')
        k = key.encode('utf-8')
        self.__db.Delete(k)

    def __iter__(self):
        for k in self.__db.RangeIter(include_value=False):
            yield k.decode('utf-8')

    def keys(self):
        return self.__iter__()

    def items(self):
        for k, v in self.__db.RangeIter():
            yield k.decode('utf-8'), json.loads(v.decode('utf-8'))

    def writebatch(self, values):
        batch = leveldb.WriteBatch()
        for key, value in values.items():
            if not isinstance(key, str):
                raise DBException('Key should be str')
            if not isinstance(value, dict):
                raise DBException('Value should be dict')
            batch.Put(key.encode('utf-8'), json.dumps(value).encode('utf-8'))
        self.__db.Write(batch)


class Table(metaclass=Cached):

    def __init__(self, name, dbroot=None, data_type=None):
        logger.info('Init DB table {}(type={}) at {}'.format(name, data_type, dbroot))
        if dbroot is None:
            logger.error('Can not create Table: database was not init with root dir')
            raise DBException('Can not create Table: database was not init with root dir')
        self._path = os.path.join(dbroot, name)
        if data_type == 'dict':
            self._table = LevelDBJsonDict(self._path)
        elif data_type == 'bytes':
            self._table = LevelDBDict(self._path)
        else:
            self._table = LevelDBDict(self._path)

    def __repr__(self):
        return 'Table({}) object at {}'.format(self._path, id(self))

    def __str__(self):
        return 'Table({})'.format(self._path)

    def get(self, key):
        return self._table.get(key)

    def put(self, key, value):
        self._table[key] = value

    def delete(self, key):
        del self._table[key]

    def all(self):
        return [v for k, v in self._table.items()]

    def keys(self):
        return [k for k in self._table.keys()]


class Database(object):
    def __init__(self, dbroot=None, create_if_missing=False):
        self._dbroot = dbroot
        if dbroot is not None and not os.path.exists(self._dbroot):
            if create_if_missing:
                logger.info('The DB root dir {} is not exists, auto created.'.format(self._dbroot))
                os.makedirs(self._dbroot)
            else:
                raise DBException('The DB folder')

    def init_app(self, app):
        try:
            self._dbroot = app.config['DB_ROOT']
            if not os.path.exists(self._dbroot):
                logger.warning('The DB root dir {} is not exists, auto created.'.format(self._dbroot))
                os.makedirs(self._dbroot)
        except Exception as err:
            logger.error('Database init failed: {}'.format(err))

    def __repr__(self):
        return 'Database({}) object at {}'.format(self._dbroot, id(self))

    def __str__(self):
        return 'Database({})'.format(self._dbroot)

    def __getattr__(self, name):
        """
        Get a table of this database by name.
        :Parameters:
          - `name`: the name of the table to get
        """
        return Table(name, self._dbroot, 'dict')

    def __getitem__(self, name):
        """
        Get a table of this database by name.
        :Parameters:
          - `name`: the name of the table to get
        """
        return self.__getattr__(name, self._dbroot, 'dict')

    def table(self, name, data_type):
        return Table(name, self._dbroot, data_type)

    def drop(self):
        """
        Drop the dababase
        """
        shutil.rmtree(self._dbroot, ignore_errors=True)

    def path(self):
        return self._dbroot
