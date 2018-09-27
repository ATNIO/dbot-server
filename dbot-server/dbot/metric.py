#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dbot_metrics import BaseMetric
from dbot_metrics import MetricException
import datetime
#  import threading


class DbotApiInfo():
    def __init__(self, name, user):
        self.name = name
        self.user = user
        ## options for one call
        self.latency = 0
        self.errcode = 0
        ## options for calls during an interval
        self.called_times = 0
        self.errors = 0
        self.latencytotal = 0

class DBotApiMetric(BaseMetric):
    ERROR_SUCCESS = 200
    def __init__(self):
        #  self.__api_mutex = threading.Lock()
        self.__dbot_api = {}
        self.__notify = None
        self.__name = "apimetric"
        self.__collect_interval = 10
        self.time_counter = 0
        self.__enable_detail = True

    def Init(self, options):
        collect_interval = options.get("interval")
        self.__collect_interval = int(collect_interval)

    def GetName(self):
        return self.__name

    def GetCollectInterval(self):
        return self.__collect_interval

    def RegisterNotify(self, notify):
        self.__notify = notify

    def EnableDetailRecord(self, flag):
        self.__enable_detail = flag

    def CallBegin(self, name, user):
        # start time
        key = name + "@" + user
        #  with self.__api_mutex:
        dbotapi = DbotApiInfo(name, user)
        dbotapi.latency = datetime.datetime.now()
        dbotapi.errcode = self.ERROR_SUCCESS
        return dbotapi

    def CallEnd(self, dbotapi, errcode):
        dbotapi.errcode = errcode
        timedelta = datetime.datetime.now() - dbotapi.latency
        dbotapi.latency = (float(timedelta.microseconds)/10**6 + timedelta.seconds)
        if self.__enable_detail:
            self.__notifyCalled(dbotapi)

        key = dbotapi.name + "@" + dbotapi.user
        saved = self.__dbot_api.get(key, None)
        if saved is None:
            self.__dbot_api[key] = dbotapi
        self.__dbot_api[key].latencytotal += dbotapi.latency
        self.__dbot_api[key].called_times += 1
        if errcode != self.ERROR_SUCCESS:
            self.__dbot_api[key].errors += 1

    def FetchInfo(self):
        info = []
        for _, api in self.__dbot_api.items():
            latencyavg = (0 if api.called_times == 0 else api.latencytotal/api.called_times)
            keys = {'name':api.name, 'user':api.user}
            values = {'latency':latencyavg, 'calltimes':api.called_times, 'errors':api.errors}
            info.append({'target': 'apicallinterval', 'keys': keys, 'values': values})
            api.latencytotal = 0
            api.called_times = 0
            api.errors = 0
        return info

    def __notifyCalled(self, dbotapi):
        keys = {'name': dbotapi.name, 'user': dbotapi.user}
        values = {'latency': dbotapi.latency, 'errcode':dbotapi.errcode}
        self.__notify({'target': 'apicall', 'keys':keys, 'values':values}, False)
