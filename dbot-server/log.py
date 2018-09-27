#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
from logging.handlers import TimedRotatingFileHandler


class DbotLogger(logging.Logger):
    def __init__(self,name,level="DEBUG",stream=True,files=True):
        self.name = name
        self.level = level
        logging.Logger.__init__(self,self.name,level=self.level)
        if stream:
            self.__streamHandler__(self.level)
        if files:
            self.__filesHandler__(self.level)

    def __streamHandler__(self,level=None):
        handler = TimedRotatingFileHandler(filename=self.name+".log", when='D', interval=1, backupCount=15)
        handler.suffix = '%Y%m%d.log'
        handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def __filesHandler__(self,level=None):
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        handler.setLevel(level)
        self.addHandler(handler)

     #  if __name__ == '__main__':
     #      log = MylogHandler('test')
     #      log.info('this is a my log handler')
